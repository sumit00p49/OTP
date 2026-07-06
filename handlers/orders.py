"""
Handler for order history and order details.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.inline import orders_list_keyboard, order_detail_keyboard, back_to_main_keyboard
from utils.formatters import format_order_list_header, format_order_detail, format_no_orders
from services.order_service import get_user_orders, get_order_details, get_user_order_count

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

    await callback.message.edit_text(
        format_order_detail(order),
        reply_markup=order_detail_keyboard(order_id),
        parse_mode="HTML",
    )
    await callback.answer()
