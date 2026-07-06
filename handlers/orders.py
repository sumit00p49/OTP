"""
Handler for order history and order details.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.inline import orders_list_keyboard, order_detail_keyboard, back_to_main_keyboard
from utils.formatters import (
    format_order_list_header,
    format_order_detail,
    format_no_orders,
    format_live_otp,
    format_otp_not_ready,
)
from services.order_service import get_user_orders, get_order_details, get_user_order_count
from services.lzt_api import lzt_api, LZTAPIError

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "my_orders")
async def my_orders(callback: CallbackQuery):
    """Show order history."""
    user_id = callback.from_user.id
    orders = await get_user_orders(user_id, limit=50)

    if not orders:
        await callback.message.edit_text(
            format_no_orders(),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    count = await get_user_order_count(user_id)
    text = format_order_list_header(count)

    await callback.message.edit_text(
        text,
        reply_markup=orders_list_keyboard(orders, page=0),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("orders_page:"))
async def orders_pagination(callback: CallbackQuery):
    """Handle order list pagination."""
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    orders = await get_user_orders(user_id, limit=50)
    count = await get_user_order_count(user_id)

    text = format_order_list_header(count)

    await callback.message.edit_text(
        text,
        reply_markup=orders_list_keyboard(orders, page=page),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order_detail:"))
async def order_detail(callback: CallbackQuery):
    """Show details for a specific order."""
    order_id = callback.data.replace("order_detail:", "")
    order = await get_order_details(order_id)

    if not order:
        await callback.answer("❌ Order not found", show_alert=True)
        return

    item_id = str(order.get("lzt_item_id", "") or "")
    await callback.message.edit_text(
        format_order_detail(order),
        reply_markup=order_detail_keyboard(order_id, item_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("get_otp:"))
async def get_live_otp(callback: CallbackQuery):
    """Fetch the latest live OTP / Telegram login code for an account."""
    item_id = callback.data.replace("get_otp:", "")
    if not item_id:
        await callback.answer("❌ Invalid account.", show_alert=True)
        return

    await callback.answer("🔄 Fetching live OTP...")

    try:
        code = await lzt_api.get_telegram_login_code(item_id)
    except LZTAPIError as e:
        logger.warning("OTP fetch failed for item %s: %s", item_id, e.message)
        await callback.message.answer(
            format_otp_not_ready(), parse_mode="HTML"
        )
        return

    if code:
        # Send as a fresh, copyable message (each fetch is a new live code)
        await callback.message.answer(
            format_live_otp(code), parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            format_otp_not_ready(), parse_mode="HTML"
        )
