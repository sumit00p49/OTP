"""
FSM States for the deposit flow.
"""

from aiogram.fsm.state import State, StatesGroup


class DepositStates(StatesGroup):
    """States for deposit process."""
    waiting_amount = State()        # Waiting for user to enter amount
    waiting_screenshot = State()    # Waiting for payment screenshot


class ShopStates(StatesGroup):
    """States for shop search flow."""
    waiting_country_search = State()  # Waiting for country name input
