"""
Account Preview - shows account info before purchase.
Uses LZT search data to display what user is getting.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.lzt_api import lzt_api, LZTAPIError
from services.product_manager import get_product
from keyboards.inline import back_to_main_keyboard

router = Router()


@router.callback_query(F.data.startswith("preview_stock:"))
async def preview_stock(callback: CallbackQuery):
    """Preview what accounts look like for a country."""
    code = callback.data.split(":")[1]
    product = get_product(code)
    if not product:
        return await callback.answer("❌ Not found", show_alert=True)

    try:
        items = await lzt_api.search_accounts(
            country=code,
            pmax=product.get("max_lzt"),
            extra_filters=product.get("filters", {}),
        )
    except LZTAPIError:
        items = []

    if not items:
        await callback.answer("📭 No stock to preview", show_alert=True)
        return

    # Show first 3 items as preview
    msg = f"📱 <b>Account Preview — {product['flag']} {product['name']}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i, item in enumerate(items[:3], 1):
        title = item.get("title_en") or item.get("title", "N/A")
        price = item.get("price", 0)
        origin = item.get("item_origin", "?")
        last_seen = item.get("telegram_last_seen", 0)
        contacts = item.get("telegram_contacts_count", 0)
        premium = "⭐" if item.get("telegram_premium") else "—"
        spam = "🟢 No" if item.get("nsb") else ("🔴 Yes" if item.get("telegram_spam_block") else "⚪ Unknown")

        # Time since last seen
        import time
        if last_seen:
            diff = int(time.time()) - last_seen
            if diff < 3600:
                seen_str = f"{diff // 60}m ago"
            elif diff < 86400:
                seen_str = f"{diff // 3600}h ago"
            else:
                seen_str = f"{diff // 86400}d ago"
        else:
            seen_str = "Unknown"

        msg += (
            f"<b>#{i}</b> — ${price}\n"
            f"  📦 Origin: {origin}\n"
            f"  🕐 Last seen: {seen_str}\n"
            f"  👥 Contacts: {contacts}\n"
            f"  ⭐ Premium: {premium}\n"
            f"  🚫 Spam block: {spam}\n\n"
        )

    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 <i>This is a sample. Actual account may differ.</i>"

    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=f"🛒 Buy {product['name']}", callback_data=f"select_country:{code}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="buy_account"))
    await callback.message.edit_text(msg, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()
