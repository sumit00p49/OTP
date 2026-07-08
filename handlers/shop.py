"""
Handler for buying accounts with quantity selection.

Flow:
  Buy click → Select quantity (1/2/3/5/10/custom)
  → Show total (qty × ₹60) → Confirm
  → Buy N accounts from LZT one by one → Deliver all with Live OTP
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ACCOUNT_PRICE_INR, MAX_LZT_PRICE_USD, ACCOUNT_COUNTRY
from states.deposit_states import ShopStates
from keyboards.inline import (
    buy_country_keyboard,
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


@router.callback_query(F.data == "buy_account")
async def buy_account_start(callback: CallbackQuery, state: FSMContext):
    """Show country/product selection."""
    await state.clear()
    await callback.message.edit_text(
        format_buy_country_select(),
        reply_markup=buy_country_keyboard(ACCOUNT_PRICE_INR),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "select_india")
async def select_india(callback: CallbackQuery, state: FSMContext):
    """User selected India — ask for quantity as text input."""
    await state.set_state(ShopStates.waiting_quantity)
    await callback.message.edit_text(
        "🟢 𝖲𝖾𝗇𝖽 𝖳𝗁𝖾 𝖰𝗎𝖺𝗇𝗍𝗂𝗍𝗒 𝖸𝗈𝗎 𝖶𝖺𝗇𝗍 𝖳𝗈 𝖡𝗎𝗒:\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🌍 Country: India\n"
        f"🏷️ Per Account: ₹{ACCOUNT_PRICE_INR:.2f}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Please 𝖲𝖾𝗇𝖽 𝖳𝗁𝖾 𝖰𝗎𝖺𝗇𝗍𝗂𝗍𝗒 𝖸𝗈𝗎 𝖶𝖺𝗇𝗍 𝖳𝗈 𝖡𝗎𝗒:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qty:"))
async def quantity_selected(callback: CallbackQuery, state: FSMContext):
    """Handle quantity button click (legacy, kept for safety)."""
    value = callback.data.replace("qty:", "")
    if value == "custom":
        await state.set_state(ShopStates.waiting_quantity)
        await callback.message.edit_text(
            "𝖲𝖾𝗇𝖽 𝖳𝗁𝖾 𝖰𝗎𝖺𝗇𝗍𝗂𝗍𝗒 𝖸𝗈𝗎 𝖶𝖺𝗇𝗍 𝖳𝗈 𝖡𝗎𝗒:",
            parse_mode="HTML",
        )
        await callback.answer()
        return

    qty = int(value)
    await _show_confirmation(callback.message, callback.from_user.id, qty, edit=True)
    await callback.answer()


@router.message(ShopStates.waiting_quantity)
async def custom_quantity_input(message: Message, state: FSMContext):
    """Handle quantity text input — auto calculate total."""
    text = message.text.strip() if message.text else ""
    try:
        qty = int(text)
    except (ValueError, TypeError):
        await message.answer("⚠️ Please enter a valid number.")
        return

    if qty < 1:
        await message.answer("⚠️ Minimum quantity is 1.")
        return
    if qty > 50:
        await message.answer("⚠️ Maximum quantity is 50 per order.")
        return

    await state.clear()
    await _show_confirmation(message, message.from_user.id, qty, edit=False)


async def _show_confirmation(message, user_id: int, qty: int, edit: bool = True):
    """Show order confirmation with total amount."""
    total = ACCOUNT_PRICE_INR * qty
    balance = await get_balance(user_id)

    if balance < total:
        text = format_insufficient_balance(total, balance)
        kb = back_to_main_keyboard()
    else:
        text = format_buy_confirm(qty, ACCOUNT_PRICE_INR, total, balance)
        kb = buy_confirm_keyboard(qty, total)

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("confirm_buy:"))
async def confirm_buy(callback: CallbackQuery, state: FSMContext):
    """User confirmed purchase — buy N accounts from LZT."""
    qty = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    total = ACCOUNT_PRICE_INR * qty

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

    # 2) Buy accounts one by one
    delivered = []
    failed_count = 0

    for i in range(qty):
        try:
            items = await lzt_api.search_accounts(
                country=ACCOUNT_COUNTRY,
                pmax=MAX_LZT_PRICE_USD,
            )
            if not items:
                failed_count += 1
                continue

            item = items[0]
            item_id = item.get("item_id", item.get("id"))
            lzt_price = float(item.get("price", 0))

            buy_result = await lzt_api.buy(item_id, price=lzt_price, currency="usd")

            # After buying, fetch full item details (has phone number clearly)
            try:
                item_details = await lzt_api.get_item(item_id)
                account_data = lzt_api.extract_account_data(item_details)
            except Exception:
                # Fallback to buy response
                account_data = lzt_api.extract_account_data(buy_result)

            # Log raw response for debugging (first few purchases)
            logger.info("Purchase #%d item %s - phone: %s", i + 1, item_id, account_data.get("phone"))

            # Best-effort: fetch login code
            login_code = await lzt_api.get_telegram_login_code(item_id)
            if login_code:
                account_data["login_code"] = login_code

            # Save order
            order_id = await create_order(
                user_id=user_id,
                lzt_item_id=str(item_id),
                amount_paid=ACCOUNT_PRICE_INR,
                account_data=account_data,
                quality="india_premium",
                country=ACCOUNT_COUNTRY,
            )
            delivered.append({"order_id": order_id, "item_id": str(item_id), "data": account_data})

        except LZTAPIError as e:
            logger.warning("Buy #%d failed for user %s: %s", i + 1, user_id, e.message)
            failed_count += 1
        except Exception as e:
            logger.exception("Unexpected error buying #%d for user %s", i + 1, user_id)
            failed_count += 1

    # 3) Refund for failed ones
    if failed_count > 0:
        refund_amount = ACCOUNT_PRICE_INR * failed_count
        await credit(user_id, refund_amount)

    # 4) Deliver results
    if not delivered:
        # All failed
        await callback.message.edit_text(
            format_out_of_stock(),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    if len(delivered) == 1:
        # Single account - simple view
        d = delivered[0]
        await callback.message.edit_text(
            format_account_details(d["order_id"], d["data"], ACCOUNT_PRICE_INR),
            reply_markup=account_delivered_keyboard(d["order_id"], d["item_id"]),
            parse_mode="HTML",
        )
    else:
        # Multiple accounts - bulk view
        if failed_count > 0:
            header = format_partial_delivery(len(delivered), failed_count, ACCOUNT_PRICE_INR * failed_count)
        else:
            header = ""
        msg = format_multi_account_details(delivered, ACCOUNT_PRICE_INR, header)
        await callback.message.edit_text(
            msg,
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        # Also send each account separately so user can use Live OTP
        for d in delivered:
            await callback.message.answer(
                format_account_details(d["order_id"], d["data"], ACCOUNT_PRICE_INR),
                reply_markup=account_delivered_keyboard(d["order_id"], d["item_id"]),
                parse_mode="HTML",
            )
