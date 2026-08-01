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
import time
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

# Short-lived stock cache so repeated /start loads are INSTANT.
# code -> (count, timestamp)
_stock_cache: dict = {}
_STOCK_TTL = 90          # seconds a cached count stays fresh
_STOCK_CONCURRENCY = 3   # how many countries to check at once (balance speed vs rate limit)


async def get_live_stock(products: list) -> dict:
    """
    Fetch stock counts with a 90s cache + limited concurrency.

    - Cached counts (fresh within 90s) are returned INSTANTLY (no API call).
    - Only stale/missing countries are fetched, max 3 at a time (fast, but
      stays under LZT's rate limit so no country wrongly shows 0).
    """
    now = time.time()
    stock: dict = {}
    to_fetch = []

    for p in products:
        code = p["code"]
        cached = _stock_cache.get(code)
        if cached and (now - cached[1]) < _STOCK_TTL:
            stock[code] = cached[0]      # fresh cache hit -> instant
        else:
            to_fetch.append(p)

    if to_fetch:
        sem = asyncio.Semaphore(_STOCK_CONCURRENCY)

        async def _get(p):
            code = p["code"]
            async with sem:
                try:
                    effective = get_effective_filters(p)
                    # Count only accounts WITHIN max_lzt (the real buyable stock).
                    # No fake/inflated numbers — what's shown can actually be bought.
                    count = await lzt_api.get_stock_count(
                        country=code,
                        pmax=p.get("max_lzt"),
                        extra_filters=effective,
                    )
                except Exception as e:
                    logger.warning("Stock fetch error for %s: %s", code, e)
                    # Fall back to last known count instead of 0
                    count = _stock_cache.get(code, (0, 0))[0]
                _stock_cache[code] = (count, time.time())
                return code, count

        results = await asyncio.gather(*[_get(p) for p in to_fetch], return_exceptions=True)
        for r in results:
            if isinstance(r, tuple):
                stock[r[0]] = r[1]

    return stock


COUNTRIES_PER_PAGE = 7


@router.callback_query(F.data == "buy_account")
async def buy_account_start(callback: CallbackQuery, state: FSMContext):
    """Show page 0 of country/product selection."""
    await state.clear()
    await _show_buy_page(callback, page=0)


@router.callback_query(F.data.startswith("buy_page:"))
async def buy_page(callback: CallbackQuery):
    """Handle pagination on the buy-account country list."""
    page = int(callback.data.split(":")[1])
    await _show_buy_page(callback, page=page)


async def _show_buy_page(callback: CallbackQuery, page: int = 0):
    """Render one page of the country list with stock counts."""
    products = get_all_products()
    stock_counts = await get_live_stock(products)

    total = len(products)
    start = page * COUNTRIES_PER_PAGE
    end = start + COUNTRIES_PER_PAGE
    page_products = products[start:end]

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()

    for p in page_products:
        flag = p.get("flag", "\U0001f30d")
        name = p.get("name", p["code"])
        price = p.get("price", 0)
        code = p["code"]
        stock = stock_counts.get(code, 0)
        stock_text = f"{stock} in stock" if stock > 0 else "Out of stock"
        # Original clean format
        btn_text = f"{flag} {name}  —  \u20b9{price:.0f}  ({stock_text})"
        builder.row(
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"select_country:{code}",
            )
        )

    # Pagination buttons — only show what's needed
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="\u25c0\ufe0f Previous", callback_data=f"buy_page:{page - 1}"))
    nav.append(InlineKeyboardButton(text="\U0001f3e0 Menu", callback_data="back_main"))
    if end < total:
        nav.append(InlineKeyboardButton(text="Next \u25b6\ufe0f", callback_data=f"buy_page:{page + 1}"))
    builder.row(*nav)

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
    
    # Live progress message
    progress_msg = await callback.message.edit_text(
        f"⏳ <b>Processing purchase...</b>\n\n"
        f"🔍 Searching for clean accounts...\n"
        f"📦 Quantity: {qty}\n"
        f"🌍 Country: {country_code}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Attempt 1/5 — Searching...",
        parse_mode="HTML",
    )

    # 1) Debit full amount upfront
    success, _ = await debit(user_id, total)
    if not success:
        bal = await get_balance(user_id)
        await progress_msg.edit_text(
            format_insufficient_balance(total, bal),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    # 2) Buy accounts with STRICT pre-verification + 5 retries + live updates
    delivered = []
    failed_count = 0
    MAX_ATTEMPTS = 5  # Max 5 attempts per account slot

    for i in range(qty):
        bought = False
        
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                # LIVE UPDATE — user sees every attempt
                await progress_msg.edit_text(
                    f"⏳ <b>Buying account {i+1}/{qty}...</b>\n\n"
                    f"🔄 Attempt {attempt}/{MAX_ATTEMPTS}\n"
                    f"🔍 Searching clean account...\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ Delivered: {len(delivered)}\n"
                    f"❌ Failed: {failed_count}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━",
                    parse_mode="HTML",
                )

                logger.info(
                    "Searching item #%d (attempt %d/5) for %s: pmax=$%.2f, filters=%s",
                    i + 1, attempt, country_code, max_lzt, effective_filters,
                )

                items = await lzt_api.search_accounts(
                    country=country_code,
                    pmax=max_lzt,
                    extra_filters=effective_filters,
                )

                if not items:
                    logger.warning("No stock for %s with filters %s", country_code, effective_filters)
                    # Update live text
                    await progress_msg.edit_text(
                        f"⏳ <b>Buying account {i+1}/{qty}...</b>\n\n"
                        f"🔄 Attempt {attempt}/{MAX_ATTEMPTS}\n"
                        f"📭 No stock found, retrying...\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"✅ Delivered: {len(delivered)}\n"
                        f"❌ Failed: {failed_count}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━",
                        parse_mode="HTML",
                    )
                    import asyncio
                    await asyncio.sleep(2)
                    continue  # Retry

                # SCAN through ALL items to find first CLEAN one
                # Skip items we already bought in previous slots
                bought_ids = {d["item_id"] for d in delivered}
                clean_item = None
                scanned = 0
                
                for candidate in items:
                    cand_id = str(candidate.get("item_id", candidate.get("id", "")))
                    if cand_id in bought_ids:
                        continue  # Already bought this one
                    
                    is_valid, reason = await lzt_api.verify_account_before_buy(candidate)
                    scanned += 1
                    if is_valid:
                        clean_item = candidate
                        break
                    else:
                        logger.info("Skipping item %s: %s", cand_id, reason)
                
                if not clean_item:
                    logger.warning("All %d items in results have spam block (attempt %d)", scanned, attempt)
                    await progress_msg.edit_text(
                        f"⏳ <b>Buying account {i+1}/{qty}...</b>\n\n"
                        f"🔄 Attempt {attempt}/{MAX_ATTEMPTS}\n"
                        f"⚠️ Scanned {scanned} accounts — all have spam block\n"
                        f"🔍 Retrying with different search...\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"✅ Delivered: {len(delivered)}\n"
                        f"❌ Failed: {failed_count}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━",
                        parse_mode="HTML",
                    )
                    import asyncio
                    await asyncio.sleep(2)
                    continue  # Retry with next attempt

                item = clean_item
                item_id = item.get("item_id", item.get("id"))

                # ========== VERIFIED CLEAN — NOW BUY ==========
                lzt_price = float(item.get("price", 0))

                await progress_msg.edit_text(
                    f"⏳ <b>Buying account {i+1}/{qty}...</b>\n\n"
                    f"🔄 Attempt {attempt}/{MAX_ATTEMPTS}\n"
                    f"✅ Clean account found!\n"
                    f"💰 Purchasing ${lzt_price:.2f}...\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ Delivered: {len(delivered)}\n"
                    f"❌ Failed: {failed_count}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━",
                    parse_mode="HTML",
                )

                buy_result = await lzt_api.buy(item_id, price=lzt_price, currency="usd")

                # Fetch full item details
                try:
                    item_details = await lzt_api.get_item(item_id)
                    account_data = lzt_api.extract_account_data(item_details)
                except Exception as e:
                    logger.warning("get_item failed after buy: %s", e)
                    account_data = lzt_api.extract_account_data(buy_result)

                logger.info("Purchase #%d SUCCESS item %s - phone=%s ✅", i + 1, item_id, account_data.get("phone"))

                # Fetch login code
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
                break  # SUCCESS — move to next account

            except LZTAPIError as e:
                logger.warning("Buy #%d attempt %d failed: %s", i + 1, attempt, e.message)
                await progress_msg.edit_text(
                    f"⏳ <b>Buying account {i+1}/{qty}...</b>\n\n"
                    f"🔄 Attempt {attempt}/{MAX_ATTEMPTS}\n"
                    f"⚠️ Error: {e.message[:50]}\n"
                    f"🔄 Retrying...\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ Delivered: {len(delivered)}\n"
                    f"❌ Failed: {failed_count}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━",
                    parse_mode="HTML",
                )
                import asyncio
                await asyncio.sleep(2)
            except Exception as e:
                logger.exception("Unexpected error buying #%d attempt %d", i + 1, attempt)
                import asyncio
                await asyncio.sleep(2)

        if not bought:
            failed_count += 1

    # 3) Refund for failed ones
    if failed_count > 0:
        refund_amount = price_per * failed_count
        await credit(user_id, refund_amount)

    # 4) Deliver results
    if not delivered:
        await progress_msg.edit_text(
            format_out_of_stock(),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    if len(delivered) == 1:
        d = delivered[0]
        await progress_msg.edit_text(
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
        await progress_msg.edit_text(
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
