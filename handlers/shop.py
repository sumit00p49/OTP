"""
Handler for buying accounts with multi-country support.

Flow:
  Buy -> Select country (dynamic from PRODUCTS config)
  -> Enter quantity -> Confirm (total calculated)
  -> Buy from LZT with EFFECTIVE filters -> Verify -> Deliver with OTP

IMPORTANT: Filters are auto-applied from GLOBAL_DEFAULT_FILTERS + product-specific.
Stock shown = REAL stock with same filters as purchase (no fake numbers).
"""

import logging
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from services.product_manager import get_all_products, get_product, get_effective_filters
from states.deposit_states import ShopStates
from keyboards.inline import (
    buy_confirm_keyboard,
    account_delivered_keyboard,
    back_to_main_keyboard,
)
from utils.formatters import (
    format_buy_country_select,
    format_buy_confirm,
    format_purchase_processing_multi,
    format_account_details,
    format_multi_account_details,
    format_purchase_failed_refund,
    format_partial_delivery,
    format_out_of_stock,
    format_insufficient_balance,
)
from services.wallet import get_balance, debit, credit
from services.lzt_api import lzt_api, LZTAPIError
from services.order_service import create_order

logger = logging.getLogger(__name__)
router = Router()


# ==================== Stock Fetch (LIVE with REAL filters) ====================

async def get_live_stock(products: list) -> dict:
    """
    Fetch stock counts LIVE from API with EXACT same filters used for purchase.
    This ensures stock number is REAL - no fake counts.
    """
    async def _get(p):
        effective = get_effective_filters(p)
        return p["code"], await lzt_api.get_stock_count(
            country=p["code"],
            pmax=p.get("max_lzt"),
            extra_filters=effective,
        )

    try:
        results = await asyncio.gather(*[_get(p) for p in products], return_exceptions=True)
        stock = {}
        for r in results:
            if isinstance(r, tuple):
                stock[r[0]] = r[1]
            elif isinstance(r, Exception):
                logger.warning("Stock fetch error: %s", r)
        return stock
    except Exception as e:
        logger.error("get_live_stock failed: %s", e)
        return {}


@router.callback_query(F.data == "buy_account")
async def buy_account_start(callback: CallbackQuery, state: FSMContext):
    """Show country/product selection with REAL stock counts."""
    await state.clear()

    products = get_all_products()
    stock_counts = await get_live_stock(products)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()

    for p in products:
        flag = p.get("flag", "\U0001f30d")
        name = p.get("name", p["code"])
        price = p.get("price", 0)
        code = p["code"]
        stock = stock_counts.get(code, 0)

        # Show stock accurately - 0 means genuinely out of stock
        stock_text = f"{stock} in stock" if stock > 0 else "Out of stock"
        builder.row(
            InlineKeyboardButton(
                text=f"{flag} {name}  \u2014  \u20b9{price:.0f}  ({stock_text})",
                callback_data=f"select_country:{code}",
            )
        )

    builder.row(
        InlineKeyboardButton(text="\u2b05\ufe0f \U0001d5d5\U0001d5ee\U0001d5f0\U0001d5f8", callback_data="back_main")
    )

    await callback.message.edit_text(
        format_buy_country_select(),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_country:"))
async def select_country(callback: CallbackQuery, state: FSMContext):
    """User selected a country - ask for quantity."""
    country_code = callback.data.split(":")[1]
    product = get_product(country_code)

    if not product:
        await callback.answer("\u274c Country not found", show_alert=True)
        return

    await state.update_data(selected_country=country_code)
    await state.set_state(ShopStates.waiting_quantity)

    price = product["price"]
    name = product.get("name", country_code)
    flag = product.get("flag", "\U0001f30d")

    await callback.message.edit_text(
        f"\U0001f7e2 \U0001d5b2\U0001d5f2\U0001d5fb\U0001d5f1 \U0001d5e7\U0001d5f5\U0001d5f2 \U0001d5e4\U0001d5f4\U0001d5ee\U0001d5fb\U0001d5f9\U0001d5f6\U0001d5f9\U0001d5f0 \U0001d5ec\U0001d5fc\U0001d5f4 \U0001d5ea\U0001d5ee\U0001d5fb\U0001d5f9 \U0001d5e7\U0001d5fc \U0001d5d5\U0001d5f4\U0001d5f0:\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"\U0001f30d Country: {flag} {name}\n"
        f"\U0001f3f7\ufe0f Per Account: \u20b9{price:.2f}\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "Please send the quantity you want to buy:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ShopStates.waiting_quantity)
async def quantity_input(message: Message, state: FSMContext):
    """Handle quantity text input - auto calculate total."""
    text = message.text.strip() if message.text else ""
    try:
        qty = int(text)
    except (ValueError, TypeError):
        await message.answer("\u26a0\ufe0f Please enter a valid number.")
        return

    if qty < 1:
        await message.answer("\u26a0\ufe0f Minimum quantity is 1.")
        return
    if qty > 50:
        await message.answer("\u26a0\ufe0f Maximum quantity is 50 per order.")
        return

    data = await state.get_data()
    country_code = data.get("selected_country", "IN")
    await state.clear()
    await _show_confirmation(message, message.from_user.id, qty, country_code)


async def _show_confirmation(message, user_id: int, qty: int, country_code: str):
    """Show order confirmation with total amount."""
    product = get_product(country_code)
    price_per = product["price"]
    total = price_per * qty

    balance = await get_balance(user_id)

    if balance < total:
        await message.answer(
            format_insufficient_balance(total, balance),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    name = product.get("name", country_code)
    flag = product.get("flag", "\U0001f30d")
    text = format_buy_confirm(qty, price_per, total, balance, f"{flag} {name}")

    await message.answer(
        text,
        reply_markup=buy_confirm_keyboard(qty, total, country_code),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("confirm_buy:"))
async def confirm_buy(callback: CallbackQuery, state: FSMContext):
    """
    User confirmed purchase - buy N accounts from LZT with EFFECTIVE filters.
    
    FLOW:
    1. Search with effective filters (nsb=1, telegram_password=0, eg=1 + extras)
    2. Verify each account before buying (no spam block, valid)
    3. Buy only verified accounts
    4. Deliver with OTP button
    """
    parts = callback.data.split(":")
    qty = int(parts[1])
    country_code = parts[2] if len(parts) > 2 else "IN"

    product = get_product(country_code)
    price_per = product["price"]
    total = price_per * qty
    user_id = callback.from_user.id
    max_lzt = product.get("max_lzt", 1.00)

    # Get EFFECTIVE filters (global defaults + product-specific)
    effective_filters = get_effective_filters(product)

    # Fix country code
    from services.lzt_api import _fix_country_code
    actual_country = _fix_country_code(country_code)

    logger.info(
        "BUY: user=%s, country=%s (api=%s), qty=%d, max_lzt=$%.2f, filters=%s",
        user_id, country_code, actual_country, qty, max_lzt, effective_filters
    )

    # Double-check balance
    balance = await get_balance(user_id)
    if balance < total:
        await callback.message.edit_text(
            format_insufficient_balance(total, balance),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.answer()
    await callback.message.edit_text(
        format_purchase_processing_multi(qty), parse_mode="HTML"
    )

    # 1) Debit full amount upfront
    success, _ = await debit(user_id, total)
    if not success:
        bal = await get_balance(user_id)
        await callback.message.edit_text(
            format_insufficient_balance(total, bal),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    # 2) Buy accounts one by one with VERIFICATION
    delivered = []
    failed_count = 0
    max_retries_per_slot = 3  # Try up to 3 items per slot to find a good one

    for i in range(qty):
        bought = False
        for attempt in range(max_retries_per_slot):
            try:
                logger.info(
                    "Searching item #%d (attempt %d) for %s: pmax=$%.2f, filters=%s",
                    i + 1, attempt + 1, country_code, max_lzt, effective_filters,
                )
                items = await lzt_api.search_accounts(
                    country=country_code,
                    pmax=max_lzt,
                    extra_filters=effective_filters,
                )
                if not items:
                    logger.warning("No stock for %s with filters %s", country_code, effective_filters)
                    break  # No stock at all, don't retry

                # Skip already-attempted items
                item = items[attempt] if attempt < len(items) else items[0]
                item_id = item.get("item_id", item.get("id"))

                # VERIFY before buying
                is_valid, reason = await lzt_api.verify_account_before_buy(item)
                if not is_valid:
                    logger.warning("Item %s failed verification: %s, trying next", item_id, reason)
                    continue

                lzt_price = float(item.get("price", 0))

                # BUY
                buy_result = await lzt_api.buy(item_id, price=lzt_price, currency="usd")

                # Fetch full item details (phone only visible after purchase)
                try:
                    item_details = await lzt_api.get_item(item_id)
                    account_data = lzt_api.extract_account_data(item_details)
                except Exception as e:
                    logger.warning("get_item failed after buy: %s", e)
                    account_data = lzt_api.extract_account_data(buy_result)

                logger.info("Purchase #%d item %s - phone=%s", i + 1, item_id, account_data.get("phone"))

                # Best-effort: fetch login code
                login_code = await lzt_api.get_telegram_login_code(item_id)
                if login_code:
                    account_data["login_code"] = login_code

                # Save order
                order_id = await create_order(
                    user_id=user_id,
                    lzt_item_id=str(item_id),
                    amount_paid=price_per,
                    account_data=account_data,
                    quality=f"{country_code}_account",
                    country=country_code,
                )
                delivered.append({"order_id": order_id, "item_id": str(item_id), "data": account_data})
                bought = True
                break  # Success, move to next slot

            except LZTAPIError as e:
                logger.warning("Buy #%d attempt %d failed: %s", i + 1, attempt + 1, e.message)
                if attempt == max_retries_per_slot - 1:
                    break
            except Exception as e:
                logger.exception("Unexpected error buying #%d attempt %d", i + 1, attempt + 1)
                if attempt == max_retries_per_slot - 1:
                    break

        if not bought:
            failed_count += 1

    # 3) Refund for failed ones
    if failed_count > 0:
        refund_amount = price_per * failed_count
        await credit(user_id, refund_amount)

    # 4) Deliver results
    if not delivered:
        await callback.message.edit_text(
            format_out_of_stock(),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    if len(delivered) == 1:
        d = delivered[0]
        await callback.message.edit_text(
            format_account_details(d["order_id"], d["data"], price_per),
            reply_markup=account_delivered_keyboard(d["order_id"], d["item_id"]),
            parse_mode="HTML",
        )
    else:
        if failed_count > 0:
            header = format_partial_delivery(len(delivered), failed_count, price_per * failed_count)
        else:
            header = ""
        msg = format_multi_account_details(delivered, price_per, header)
        await callback.message.edit_text(
            msg, reply_markup=back_to_main_keyboard(), parse_mode="HTML",
        )
        for d in delivered:
            await callback.message.answer(
                format_account_details(d["order_id"], d["data"], price_per),
                reply_markup=account_delivered_keyboard(d["order_id"], d["item_id"]),
                parse_mode="HTML",
            )


@router.callback_query(F.data == "account_ack")
async def account_acknowledged(callback: CallbackQuery, state: FSMContext):
    """User acknowledged receiving the account."""
    await state.clear()
    await callback.message.edit_text(
        "\u2705 <b>Account Received!</b>\n\n"
        "Thank you for your purchase. \U0001f389\n"
        "Your order is saved in /start \u2192 \U0001f4cb My Orders.",
        parse_mode="HTML",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("save_order:"))
async def save_order_ack(callback: CallbackQuery):
    """Acknowledge order saved."""
    order_id = callback.data.replace("save_order:", "")
    await callback.answer(f"\U0001f4cb Order {order_id} saved!", show_alert=True)
