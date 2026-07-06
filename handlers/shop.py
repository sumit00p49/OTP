"""
Handler for shop - product browsing and purchasing flow.
Quality selection → Country selection → Balance check → Buy from LZT API.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import CHEAP_ACC_PRICE, GOOD_ACC_PRICE
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
)
from services.wallet import get_balance, debit, credit
from services.lzt_api import lzt_api, LZTAPIError
from services.order_service import create_order

router = Router()


def get_price(quality: str) -> float:
    """Get price based on quality."""
    return GOOD_ACC_PRICE if quality == "good" else CHEAP_ACC_PRICE


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
    """User selected quality tier."""
    quality = callback.data.replace("quality_", "")  # 'cheap' or 'good'
    price = get_price(quality)

    await state.update_data(selected_quality=quality)

    await callback.message.edit_text(
        format_shop_country(quality, price),
        reply_markup=shop_country_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()



@router.callback_query(F.data == "country_search")
async def country_search_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt user to type country name."""
    await state.set_state(ShopStates.waiting_country_search)
    await callback.message.edit_text(
        format_country_search_prompt(),
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ShopStates.waiting_country_search)
async def country_search_input(message: Message, state: FSMContext):
    """Handle typed country name."""
    country_name = message.text.strip() if message.text else ""
    if not country_name:
        await message.answer("⚠️ Please type a valid country name.")
        return

    # Map common names to codes
    country_map = {
        "india": "IN", "usa": "US", "united states": "US",
        "indonesia": "ID", "myanmar": "MM", "bangladesh": "BD",
        "vietnam": "VN", "russia": "RU", "uk": "GB",
        "united kingdom": "GB", "brazil": "BR", "germany": "DE",
        "france": "FR", "japan": "JP", "korea": "KR",
        "south korea": "KR", "china": "CN", "pakistan": "PK",
        "philippines": "PH", "thailand": "TH", "turkey": "TR",
        "egypt": "EG", "nigeria": "NG", "mexico": "MX",
        "canada": "CA", "australia": "AU", "italy": "IT",
        "spain": "ES", "netherlands": "NL", "poland": "PL",
        "ukraine": "UA", "malaysia": "MY", "singapore": "SG",
    }

    code = country_map.get(country_name.lower(), country_name.upper()[:2])
    data = await state.get_data()
    quality = data.get("selected_quality", "cheap")
    await state.clear()

    # Process purchase
    await _process_purchase(message, quality, code)



@router.callback_query(F.data.startswith("country_"))
async def country_selected(callback: CallbackQuery, state: FSMContext):
    """User selected a country."""
    country = callback.data.replace("country_", "")  # e.g., 'IN', 'US', 'RANDOM'
    data = await state.get_data()
    quality = data.get("selected_quality", "cheap")
    await state.clear()

    await callback.answer()
    # Delete old message and process purchase
    await callback.message.delete()
    await _process_purchase(callback.message, quality, country, callback.from_user.id)


@router.callback_query(F.data.startswith("confirm_buy:"))
async def confirm_purchase(callback: CallbackQuery):
    """User confirmed purchase."""
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Invalid data", show_alert=True)
        return

    quality = parts[1]
    country = parts[2]
    user_id = callback.from_user.id
    price = get_price(quality)

    await callback.answer()
    await callback.message.edit_text(
        format_purchase_processing(),
        parse_mode="HTML",
    )

    await _execute_purchase(callback.message, user_id, quality, country, price)


@router.callback_query(F.data == "account_ack")
async def account_acknowledged(callback: CallbackQuery):
    """User acknowledged receiving account."""
    await callback.message.edit_text(
        "✅ <b>Account Received!</b>\n\n"
        "Thank you for your purchase. 🎉\n"
        "Your order is saved in /start → My Orders.",
        parse_mode="HTML",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("save_order:"))
async def save_order_ack(callback: CallbackQuery):
    """Acknowledge order saved."""
    order_id = callback.data.replace("save_order:", "")
    await callback.answer(f"📋 Order {order_id} saved to your history!", show_alert=True)



async def _process_purchase(message: Message, quality: str, country: str, user_id: int = None):
    """Process the purchase flow - check balance and confirm."""
    if user_id is None:
        user_id = message.from_user.id if message.from_user else 0

    price = get_price(quality)
    balance = await get_balance(user_id)

    if balance < price:
        await message.answer(
            format_insufficient_balance(price, balance),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    # Show confirmation
    quality_label = "⭐ Good Quality" if quality == "good" else "🎣 Cheap"
    country_label = country if country != "RANDOM" else "🌐 Random"

    confirm_text = (
        "🛒 <b>Confirm Purchase</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Quality: {quality_label}\n"
        f"🌍 Country: {country_label}\n"
        f"💵 Price: <b>₹{price:.2f}</b>\n"
        f"💳 Your Balance: ₹{balance:.2f}\n\n"
        "⚠️ <b>NO REFUNDS IN ANY CASE</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Click below to confirm:"
    )

    await message.answer(
        confirm_text,
        reply_markup=confirm_purchase_keyboard(quality, country, price),
        parse_mode="HTML",
    )


async def _execute_purchase(message: Message, user_id: int, quality: str, country: str, price: float):
    """Execute the purchase via LZT API."""
    # Debit wallet first
    success, new_balance = await debit(user_id, price)
    if not success:
        balance = await get_balance(user_id)
        await message.edit_text(
            format_insufficient_balance(price, balance),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    # Search for account on LZT
    try:
        country_param = None if country == "RANDOM" else country
        search_result = await lzt_api.search_accounts(
            country=country_param,
            quality=quality,
            limit=1,
        )

        items = search_result.get("items", [])
        if not items:
            # Refund
            await credit(user_id, price)
            await message.edit_text(
                format_purchase_failed_refund(price, "No accounts available for this region."),
                reply_markup=back_to_main_keyboard(),
                parse_mode="HTML",
            )
            return

        # Buy the first available account
        item = items[0] if isinstance(items, list) else list(items.values())[0]
        item_id = item.get("item_id", item.get("id"))

        buy_result = await lzt_api.buy_account(item_id)

        # Extract account details
        account_data = {
            "phone": buy_result.get("loginData", {}).get("login", "N/A"),
            "password": buy_result.get("loginData", {}).get("password", "N/A"),
            "2fa": buy_result.get("loginData", {}).get("2fa", ""),
            "item_id": str(item_id),
            "raw": str(buy_result.get("loginData", {})),
        }

        # Create order
        order_id = await create_order(
            user_id=user_id,
            lzt_item_id=str(item_id),
            amount_paid=price,
            account_data=account_data,
            quality=quality,
            country=country,
        )

        # Show account to user
        await message.edit_text(
            format_account_details(order_id, account_data, price),
            reply_markup=account_received_keyboard(order_id),
            parse_mode="HTML",
        )

    except LZTAPIError as e:
        # Refund on API error
        await credit(user_id, price)
        await message.edit_text(
            format_purchase_failed_refund(price, f"API Error: {e.message}"),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        # Refund on unexpected error
        await credit(user_id, price)
        await message.edit_text(
            format_purchase_failed_refund(price, f"Unexpected error: {str(e)}"),
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
