"""
Handler for shop - product browsing and purchasing flow.

Flow:
  Quality select -> Country select -> search LZT live -> quote real INR price
  -> confirm -> debit wallet -> buy from LZT -> deliver account (auto-refund on fail)
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import PRICE_MODE, CHEAP_ACC_PRICE, GOOD_ACC_PRICE, MAX_ACC_PRICE_INR
from states.deposit_states import ShopStates
from keyboards.inline import (
    shop_quality_keyboard,
    shop_country_keyboard,
    confirm_purchase_keyboard,
    account_received_keyboard,
    back_to_main_keyboard,
)
from utils.formatters import (
    format_shop_quality,
    format_shop_country,
    format_country_search_prompt,
    format_insufficient_balance,
    format_purchase_processing,
    format_account_details,
    format_purchase_failed_refund,
    format_out_of_stock,
    format_purchase_confirm,
)
from services.wallet import get_balance, debit, credit
from services.currency import to_inr
from services.lzt_api import lzt_api, LZTAPIError
from services.order_service import create_order

logger = logging.getLogger(__name__)
router = Router()


COUNTRY_MAP = {
    "india": "IN", "usa": "US", "united states": "US", "indonesia": "ID",
    "myanmar": "MM", "bangladesh": "BD", "vietnam": "VN", "russia": "RU",
    "uk": "GB", "united kingdom": "GB", "brazil": "BR", "germany": "DE",
    "france": "FR", "japan": "JP", "korea": "KR", "south korea": "KR",
    "china": "CN", "pakistan": "PK", "philippines": "PH", "thailand": "TH",
    "turkey": "TR", "egypt": "EG", "nigeria": "NG", "mexico": "MX",
    "canada": "CA", "australia": "AU", "italy": "IT", "spain": "ES",
    "netherlands": "NL", "poland": "PL", "ukraine": "UA", "malaysia": "MY",
    "singapore": "SG",
}



@router.callback_query(F.data == "shop_main")
async def shop_main(callback: CallbackQuery, state: FSMContext):
    """Show quality selection menu."""
    await state.clear()
    await callback.message.edit_text(
        format_shop_quality(),
        reply_markup=shop_quality_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("quality_"))
async def quality_selected(callback: CallbackQuery, state: FSMContext):
    """User selected quality tier -> show country grid."""
    quality = callback.data.replace("quality_", "")  # 'cheap' or 'good'
    await state.update_data(selected_quality=quality)

    await callback.message.edit_text(
        format_shop_country(quality),
        reply_markup=shop_country_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "country_search")
async def country_search_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt user to type a country name."""
    await state.set_state(ShopStates.waiting_country_search)
    await callback.message.edit_text(
        format_country_search_prompt(),
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ShopStates.waiting_country_search)
async def country_search_input(message: Message, state: FSMContext):
    """Handle a typed country name."""
    name = message.text.strip() if message.text else ""
    if not name:
        await message.answer("⚠️ Please type a valid country name.")
        return

    code = COUNTRY_MAP.get(name.lower(), name.upper()[:2])
    data = await state.get_data()
    quality = data.get("selected_quality", "cheap")
    await state.set_state(None)
    await _quote_purchase(message, state, quality, code, message.from_user.id)


@router.callback_query(F.data.startswith("country_"))
async def country_selected(callback: CallbackQuery, state: FSMContext):
    """User selected a country from the grid."""
    country = callback.data.replace("country_", "")  # 'IN', 'US', 'RANDOM', ...
    data = await state.get_data()
    quality = data.get("selected_quality", "cheap")
    await callback.answer()
    await callback.message.edit_text(
        format_purchase_processing(), parse_mode="HTML"
    )
    await _quote_purchase(callback.message, state, quality, country, callback.from_user.id)



async def _quote_purchase(message, state, quality, country, user_id, edit=True):
    """Search LZT live, compute INR price, and show a confirmation."""
    async def _out(text, markup):
        if edit:
            try:
                await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
                return
            except Exception:
                pass
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

    # 1) Search live stock
    try:
        items = await lzt_api.search_accounts(country=country, quality=quality, limit=1)
    except LZTAPIError as e:
        await _out(
            format_purchase_failed_refund(0, f"Search failed: {e.message}"),
            back_to_main_keyboard(),
        )
        return

    if not items:
        await _out(format_out_of_stock(country), back_to_main_keyboard())
        return

    item = items[0]
    item_id = item.get("item_id", item.get("id"))
    lzt_price, currency = lzt_api.extract_price(item)

    # 2) Compute INR price
    if PRICE_MODE == "fixed":
        price_inr = GOOD_ACC_PRICE if quality == "good" else CHEAP_ACC_PRICE
    else:
        price_inr = to_inr(lzt_price, currency)

    if price_inr > MAX_ACC_PRICE_INR:
        await _out(format_out_of_stock(country), back_to_main_keyboard())
        return

    # 3) Balance check
    balance = await get_balance(user_id)
    if balance < price_inr:
        await _out(
            format_insufficient_balance(price_inr, balance),
            back_to_main_keyboard(),
        )
        return

    # 4) Stash the pending purchase and ask for confirmation
    await state.update_data(
        pending_item_id=item_id,
        pending_price_inr=price_inr,
        pending_lzt_price=lzt_price,
        pending_currency=currency,
        pending_quality=quality,
        pending_country=country,
    )
    await _out(
        format_purchase_confirm(quality, country, price_inr, balance),
        confirm_purchase_keyboard(),
    )



@router.callback_query(F.data == "confirm_buy_pending")
async def confirm_purchase(callback: CallbackQuery, state: FSMContext):
    """User confirmed -> debit wallet and buy from LZT."""
    data = await state.get_data()
    item_id = data.get("pending_item_id")
    price_inr = data.get("pending_price_inr")
    lzt_price = data.get("pending_lzt_price")
    currency = data.get("pending_currency", "usd")
    quality = data.get("pending_quality", "cheap")
    country = data.get("pending_country", "RANDOM")
    user_id = callback.from_user.id

    if not item_id or price_inr is None:
        await callback.answer("⚠️ Session expired. Please start again.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(format_purchase_processing(), parse_mode="HTML")

    # 1) Debit wallet first (atomic)
    success, _ = await debit(user_id, price_inr)
    if not success:
        balance = await get_balance(user_id)
        await callback.message.edit_text(
            format_insufficient_balance(price_inr, balance),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    # 2) Buy from LZT (price guard passes the LZT-side price)
    try:
        buy_result = await lzt_api.buy(item_id, price=lzt_price, currency=currency)
        account_data = lzt_api.extract_account_data(buy_result)

        # Best-effort: fetch Telegram login code
        login_code = await lzt_api.get_telegram_login_code(item_id)
        if login_code:
            account_data["login_code"] = login_code

        order_id = await create_order(
            user_id=user_id,
            lzt_item_id=str(item_id),
            amount_paid=price_inr,
            account_data=account_data,
            quality=quality,
            country=country,
        )

        await state.clear()
        await callback.message.edit_text(
            format_account_details(order_id, account_data, price_inr),
            reply_markup=account_received_keyboard(order_id),
            parse_mode="HTML",
        )

    except LZTAPIError as e:
        await credit(user_id, price_inr)  # auto-refund
        logger.warning("Purchase failed for user %s: %s", user_id, e.message)
        await callback.message.edit_text(
            format_purchase_failed_refund(price_inr, e.message),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        await credit(user_id, price_inr)  # auto-refund
        logger.exception("Unexpected purchase error for user %s", user_id)
        await callback.message.edit_text(
            format_purchase_failed_refund(price_inr, f"Unexpected error: {str(e)}"),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )



@router.callback_query(F.data == "account_ack")
async def account_acknowledged(callback: CallbackQuery, state: FSMContext):
    """User acknowledged receiving the account."""
    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Account Received!</b>\n\n"
        "Thank you for your purchase. 🎉\n"
        "Your order is saved in /start → 📋 My Orders.",
        parse_mode="HTML",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("save_order:"))
async def save_order_ack(callback: CallbackQuery):
    """Acknowledge order saved to history."""
    order_id = callback.data.replace("save_order:", "")
    await callback.answer(f"📋 Order {order_id} is saved in your history!", show_alert=True)
