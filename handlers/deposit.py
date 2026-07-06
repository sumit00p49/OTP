"""
Handler for deposit flow.
FSM: deposit_start → enter amount → upload screenshot → admin notification.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import UPI_ID, UPI_NAME, MIN_DEPOSIT, ADMIN_GROUP_ID
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

router = Router()


@router.callback_query(F.data == "deposit_start")
async def deposit_start(callback: CallbackQuery, state: FSMContext):
    """Show deposit instructions."""
    await state.clear()
    await callback.message.edit_text(
        format_deposit_info(UPI_ID, UPI_NAME),
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
    await callback.message.edit_text(
        "❌ Deposit cancelled.",
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(DepositStates.waiting_amount)
async def deposit_receive_amount(message: Message, state: FSMContext):
    """Receive and validate deposit amount."""
    text = message.text.strip() if message.text else ""

    # Remove currency symbol if present
    text = text.replace("₹", "").replace(",", "").strip()

    try:
        amount = float(text)
    except (ValueError, TypeError):
        await message.answer(
            "⚠️ Invalid amount. Please enter a number.\n"
            f"📌 Example: <code>200</code>",
            parse_mode="HTML",
        )
        return

    if amount < MIN_DEPOSIT:
        await message.answer(
            f"⚠️ Minimum deposit is ₹{MIN_DEPOSIT:.2f}.\n"
            "Please enter a valid amount.",
            parse_mode="HTML",
        )
        return

    # Save amount to state and ask for screenshot
    await state.update_data(deposit_amount=amount)
    await state.set_state(DepositStates.waiting_screenshot)

    await message.answer(
        format_deposit_screenshot_prompt(amount),
        reply_markup=deposit_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(DepositStates.waiting_screenshot, F.photo)
async def deposit_receive_screenshot(message: Message, state: FSMContext):
    """Receive screenshot and forward to admin."""
    data = await state.get_data()
    amount = data.get("deposit_amount", 0)
    user = message.from_user

    # Get the largest photo (best quality)
    photo = message.photo[-1]
    file_id = photo.file_id

    # Save to database
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO deposits (user_id, amount, screenshot_file_id, status)
           VALUES (?, ?, ?, 'PENDING')""",
        (user.id, amount, file_id),
    )
    await db.commit()
    deposit_id = cursor.lastrowid

    # Notify admin group
    if ADMIN_GROUP_ID:
        admin_text = format_admin_deposit_notification(
            user_id=user.id,
            username=user.username or "N/A",
            first_name=user.first_name or "User",
            amount=amount,
            deposit_id=deposit_id,
        )
        keyboard = admin_deposit_keyboard(deposit_id, user.id, amount)

        # Send screenshot to admin with notification
        await message.bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=file_id,
            caption=admin_text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    # Confirm to user
    await state.clear()
    await message.answer(
        format_deposit_pending(),
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML",
    )


@router.message(DepositStates.waiting_screenshot)
async def deposit_invalid_screenshot(message: Message, state: FSMContext):
    """Handle non-photo messages during screenshot state."""
    await message.answer(
        "📸 Please send a <b>photo/screenshot</b> of your payment.\n\n"
        "⚠️ Only images are accepted.",
        reply_markup=deposit_cancel_keyboard(),
        parse_mode="HTML",
    )
