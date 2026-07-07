"""
FSM States for the deposit and shop flows.
"""

from aiogram.fsm.state import State, StatesGroup


class DepositStates(StatesGroup):
    """States for deposit process."""
    waiting_amount = State()
    waiting_screenshot = State()


class ShopStates(StatesGroup):
    """States for shop / custom quantity input."""
    waiting_quantity = State()
