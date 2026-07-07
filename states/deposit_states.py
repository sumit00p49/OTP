"""
FSM States for the deposit flow.
"""

from aiogram.fsm.state import State, StatesGroup


class DepositStates(StatesGroup):
    """States for deposit process."""
    waiting_amount = State()
    waiting_screenshot = State()
