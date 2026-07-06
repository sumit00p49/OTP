"""
Currency conversion service.
LZT Market prices accounts in RUB/USD/EUR. The bot wallet is in INR.
This module converts foreign prices to INR and applies a profit markup.
"""

import math
from config import (
    USD_TO_INR,
    RUB_TO_INR,
    EUR_TO_INR,
    MARKUP_PERCENT,
    MARKUP_FLAT_INR,
)

# Map of currency code -> INR rate
_RATES = {
    "usd": USD_TO_INR,
    "rub": RUB_TO_INR,
    "eur": EUR_TO_INR,
}


def get_rate(currency: str) -> float:
    """Get INR conversion rate for a currency code (defaults to USD)."""
    if not currency:
        return USD_TO_INR
    return _RATES.get(currency.lower().strip(), USD_TO_INR)


def to_inr(amount: float, currency: str = "usd", apply_markup: bool = True) -> float:
    """
    Convert a foreign-currency amount to INR with optional markup.

    Args:
        amount: Price in the source currency
        currency: Source currency code ('usd', 'rub', 'eur')
        apply_markup: Whether to add the profit markup

    Returns:
        INR price, rounded up to 2 decimals

    Markup formula (when apply_markup): real_inr + (real_inr * percent%) + flat.
    By default only the flat markup applies (percent defaults to 0), so the
    user pays "real price + ₹MARKUP_FLAT_INR".
    """
    rate = get_rate(currency)
    inr = float(amount) * rate
    if apply_markup:
        inr = inr * (1 + MARKUP_PERCENT / 100.0) + MARKUP_FLAT_INR
    # Round up to nearest 0.01 so we never sell below cost+markup
    return math.ceil(inr * 100) / 100.0
