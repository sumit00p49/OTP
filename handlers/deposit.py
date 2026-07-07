"""
Handler for deposit flow.
FSM: deposit_start → enter amount → upload screenshot → admin notification.

Fixes:
- Shows UPI QR code image (from URL or auto-generated)
- Properly handles screenshot + sends to admin with approve/reject
- Works even if screenshot is sent as document/file
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import URLInputFile

from config import UPI_ID, UPI_NAME, UPI_QR_URL, MIN_DEPOSIT, ADMIN_GROUP_ID, ADMIN_IDS
from states.deposit_states import DepositStates
from keyboards.inline import (
    deposit_menu_keyboard,
    deposit_cancel_keyboard,
    admin_deposit_keyboard,
    back_to_main_keyboard,
)
from utils.formatters import (
    format_deposit_info,
    format_deposit_amount_prompt,
    format_deposit_screenshot_prompt,
    format_deposit_pending,
    format_admin_deposit_notification,
)
from database import get_db

logger = logging.getLogger(__name__)
router = Router()


def _get_qr_url() -> str:
    """Get UPI QR code URL. Uses custom URL or generates via free API."""
    if UPI_QR_URL:
        return UPI_QR_URL
    # Auto-generate QR via a free API (upi://pay link encoded as QR)
    upi_link = f"upi://pay?pa={UPI_ID}&pn={UPI_NAME.replace(' ', '%20')}&cu=INR"
    return f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_link}"


@router.callback_query(F.data == "deposit_start")
async def deposit_start(callback: CallbackQuery, state: FSMContext):
    """Show deposit instructions with UPI QR code."""
    await state.clear()

    qr_url = _get_qr_url()
    deposit_text = format_deposit_info(UPI_ID, UPI_NAME)

    # Delete old message and send new one with QR photo
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer_photo(
        photo=URLInputFile(qr_url),
        caption=deposit_text,
        reply_markup=deposit_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "deposit_amount")
async def deposit_ask_amount(callback: CallbackQuery, state: FSMContext):
    """Ask user to enter deposit amount."""
    await state.set_state(DepositStates.waiting_amount)

    # Try to edit caption (if it was a photo message) or send new
    try:
        await callback.message.edit_caption(
            caption=format_deposit_amount_prompt(),
            reply_markup=deposit_cancel_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            format_deposit_amount_prompt(),
            reply_markup=deposit_cancel_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "deposit_cancel")
async def deposit_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel deposit flow."""
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "❌ Deposit cancelled.",
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DepositStates.waiting_amount)
async def deposit_receive_amount(message: Message, state: FSMContext):
    """Receive and validate deposit amount."""
    text = message.text.strip() if message.text else ""
    text = text.replace("₹", "").replace(",", "").strip()

    try:
        amount = float(text)
    except (ValueError, TypeError):
        await message.answer(
            "⚠️ Invalid amount. Please enter a number.\n"
            "📌 Example: <code>200</code>",
            parse_mode="HTML",
        )
        return

    if amount < MIN_DEPOSIT:
        await message.answer(
            f"⚠️ Minimum deposit is ₹{MIN_DEPOSIT:.0f}.\n"
            "Please enter a valid amount.",
            parse_mode="HTML",
        )
        return

    if amount > 50000:
        await message.answer(
            "⚠️ Maximum single deposit is ₹50,000.\n"
            "Please enter a smaller amount.",
            parse_mode="HTML",
        )
        return

    # Save amount and ask for screenshot
    await state.update_data(deposit_amount=amount)
    await state.set_state(DepositStates.waiting_screenshot)

    await message.answer(
        format_deposit_screenshot_prompt(amount),
        reply_markup=deposit_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(DepositStates.waiting_screenshot, F.photo)
async def deposit_receive_screenshot(message: Message, state: FSMContext):
    """Receive screenshot photo and forward to admin."""
    await _process_screenshot(message, state, message.photo[-1].file_id)


@router.message(DepositStates.waiting_screenshot, F.document)
async def deposit_receive_document(message: Message, state: FSMContext):
    """Handle screenshot sent as document/file (some users do this)."""
    doc = message.document
    if doc and doc.mime_type and doc.mime_type.startswith("image/"):
        await _process_screenshot(message, state, doc.file_id, is_document=True)
    else:
        await message.answer(
            "📸 Please send an <b>image/screenshot</b> of your payment.\n"
            "⚠️ Only images are accepted (not PDF/other files).",
            reply_markup=deposit_cancel_keyboard(),
            parse_mode="HTML",
        )


@router.message(DepositStates.waiting_screenshot)
async def deposit_invalid_screenshot(message: Message, state: FSMContext):
    """Handle non-photo messages during screenshot state."""
    await message.answer(
        "📸 Please send a <b>photo/screenshot</b> of your payment.\n\n"
        "⚠️ Only images are accepted. Send as photo, not text.",
        reply_markup=deposit_cancel_keyboard(),
        parse_mode="HTML",
    )


async def _process_screenshot(message: Message, state: FSMContext, file_id: str, is_document: bool = False):
    """Process the screenshot: save to DB and notify admin."""
    data = await state.get_data()
    amount = data.get("deposit_amount", 0)
    user = message.from_user

    if amount <= 0:
        await state.clear()
        await message.answer(
            "⚠️ Session expired. Please start deposit again.",
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML",
        )
        return

    # Save to database
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO deposits (user_id, amount, screenshot_file_id, status)
           VALUES (?, ?, ?, 'PENDING')""",
        (user.id, amount, file_id),
    )
    await db.commit()
    deposit_id = cursor.lastrowid

    # Notify admin(s)
    admin_notified = False

    # Method 1: Send to admin group
    if ADMIN_GROUP_ID and ADMIN_GROUP_ID != 0:
        try:
            admin_text = format_admin_deposit_notification(
                user_id=user.id,
                username=user.username or "N/A",
                first_name=user.first_name or "User",
                amount=amount,
                deposit_id=deposit_id,
            )
            keyboard = admin_deposit_keyboard(deposit_id, user.id, amount)

            if is_document:
                await message.bot.send_document(
                    chat_id=ADMIN_GROUP_ID,
                    document=file_id,
                    caption=admin_text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            else:
                await message.bot.send_photo(
                    chat_id=ADMIN_GROUP_ID,
                    photo=file_id,
                    caption=admin_text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            admin_notified = True
        except Exception as e:
            logger.error("Failed to send to admin group %s: %s", ADMIN_GROUP_ID, e)

    # Method 2: Fallback — DM each admin directly
    if not admin_notified and ADMIN_IDS:
        admin_text = format_admin_deposit_notification(
            user_id=user.id,
            username=user.username or "N/A",
            first_name=user.first_name or "User",
            amount=amount,
            deposit_id=deposit_id,
        )
        keyboard = admin_deposit_keyboard(deposit_id, user.id, amount)

        for admin_id in ADMIN_IDS:
            try:
                if is_document:
                    await message.bot.send_document(
                        chat_id=admin_id,
                        document=file_id,
                        caption=admin_text,
                        reply_markup=keyboard,
                        parse_mode="HTML",
                    )
                else:
                    await message.bot.send_photo(
                        chat_id=admin_id,
                        photo=file_id,
                        caption=admin_text,
                        reply_markup=keyboard,
                        parse_mode="HTML",
                    )
                admin_notified = True
            except Exception as e:
                logger.error("Failed to DM admin %s: %s", admin_id, e)

    if not admin_notified:
        logger.error("CRITICAL: Could not notify any admin for deposit #%s!", deposit_id)

    # Confirm to user
    await state.clear()
    await message.answer(
        format_deposit_pending(),
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML",
    )
