"""
Handler for deposit flow.
FSM: deposit_start → enter amount → show QR with amount → upload screenshot → admin notification.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import URLInputFile

from config import UPI_ID, UPI_NAME, MIN_DEPOSIT, ADMIN_GROUP_ID, ADMIN_IDS
from states.deposit_states import DepositStates
from keyboards.inline import (
    deposit_menu_keyboard,
    deposit_cancel_keyboard,
    deposit_check_keyboard,
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


@router.callback_query(F.data == "deposit_start")
async def deposit_start(callback: CallbackQuery, state: FSMContext):
    """Show deposit instructions (text only, no QR)."""
    await state.clear()

    deposit_text = format_deposit_info(UPI_ID, UPI_NAME)

    await callback.message.edit_text(
        deposit_text,
        reply_markup=deposit_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "deposit_amount")
async def deposit_ask_amount(callback: CallbackQuery, state: FSMContext):
    """Ask user to enter deposit amount."""
    await state.set_state(DepositStates.waiting_amount)

    await callback.message.edit_text(
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


@router.callback_query(F.data == "deposit_check_now")
async def deposit_check_now(callback: CallbackQuery, state: FSMContext):
    """User clicked Check Now — prompt to send screenshot."""
    await callback.message.answer(
        "📸 <b>Send your payment screenshot now.</b>\n\n"
        "⚠️ Make sure it clearly shows the amount and UPI reference.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DepositStates.waiting_amount)
async def deposit_receive_amount(message: Message, state: FSMContext):
    """Receive and validate deposit amount, then show QR + deposit details."""
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

    # Save amount and move to screenshot state
    await state.update_data(deposit_amount=amount)
    await state.set_state(DepositStates.waiting_screenshot)

    # Generate UPI QR with amount pre-filled
    upi_link = f"upi://pay?pa={UPI_ID}&pn={UPI_NAME.replace(' ', '%20')}&am={amount:.2f}&cu=INR"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_link}"

    # Send QR photo with deposit details as caption
    await message.answer_photo(
        photo=URLInputFile(qr_url),
        caption=format_deposit_screenshot_prompt(amount),
        reply_markup=deposit_check_keyboard(),
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
