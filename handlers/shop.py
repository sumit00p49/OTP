"""
Handler for buying accounts.
Simplified: India-only TG accounts at fixed ₹60.
One-click buy → auto-fetch from LZT → deliver with Live OTP.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import ACCOUNT_PRICE_INR, MAX_LZT_PRICE_USD, ACCOUNT_COUNTRY
from keyboards.inline import (
    buy_confirm_keyboard,
    account_delivered_keyboard,
    back_to_main_keyboard,
)
from utils.formatters import (
    format_buy_preview,
    format_purchase_processing,
    format_account_details,
    format_purchase_failed_refund,
    format_out_of_stock,
    format_insufficient_balance,
)
from services.wallet import get_balance, debit, credit
from services.lzt_api import lzt_api, LZTAPIError
from services.order_service import create_order

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "buy_account")
async def buy_account_start(callback: CallbackQuery):
    """Show purchase confirmation screen."""
    balance = await get_balance(callback.from_user.id)

    if balance < ACCOUNT_PRICE_INR:
        await callback.message.edit_text(
            format_insufficient_balance(ACCOUNT_PRICE_INR, balance),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        format_buy_preview(ACCOUNT_PRICE_INR, balance),
        reply_markup=buy_confirm_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_buy")
async def confirm_buy(callback: CallbackQuery):
    """User confirmed purchase — debit wallet & buy from LZT."""
    user_id = callback.from_user.id
    price = ACCOUNT_PRICE_INR

    # Double-check balance
    balance = await get_balance(user_id)
    if balance < price:
        await callback.message.edit_text(
            format_insufficient_balance(price, balance),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.answer()
    await callback.message.edit_text(
        format_purchase_processing(), parse_mode="HTML"
    )

    # 1) Debit wallet
    success, _ = await debit(user_id, price)
    if not success:
        bal = await get_balance(user_id)
        await callback.message.edit_text(
            format_insufficient_balance(price, bal),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    # 2) Search cheapest India account on LZT
    try:
        items = await lzt_api.search_accounts(
            country=ACCOUNT_COUNTRY,
            pmax=MAX_LZT_PRICE_USD,
        )
    except LZTAPIError as e:
        await credit(user_id, price)
        logger.warning("LZT search failed for user %s: %s", user_id, e.message)
        await callback.message.edit_text(
            format_purchase_failed_refund(price, f"Search failed: {e.message}"),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    if not items:
        await credit(user_id, price)
        await callback.message.edit_text(
            format_out_of_stock(),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    # 3) Buy the cheapest one
    item = items[0]
    item_id = item.get("item_id", item.get("id"))
    lzt_price = float(item.get("price", 0))

    try:
        buy_result = await lzt_api.buy(item_id, price=lzt_price, currency="usd")
        account_data = lzt_api.extract_account_data(buy_result)

        # Try to get live login code
        login_code = await lzt_api.get_telegram_login_code(item_id)
        if login_code:
            account_data["login_code"] = login_code

        # 4) Save order
        order_id = await create_order(
            user_id=user_id,
            lzt_item_id=str(item_id),
            amount_paid=price,
            account_data=account_data,
            quality="india_premium",
            country=ACCOUNT_COUNTRY,
        )

        # 5) Deliver to user
        await callback.message.edit_text(
            format_account_details(order_id, account_data, price),
            reply_markup=account_delivered_keyboard(order_id, str(item_id)),
            parse_mode="HTML",
        )

    except LZTAPIError as e:
        await credit(user_id, price)
        logger.warning("LZT buy failed for user %s item %s: %s", user_id, item_id, e.message)
        await callback.message.edit_text(
            format_purchase_failed_refund(price, f"Purchase failed: {e.message}"),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        await credit(user_id, price)
        logger.exception("Unexpected purchase error for user %s", user_id)
        await callback.message.edit_text(
            format_purchase_failed_refund(price, f"Unexpected error: {str(e)}"),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
