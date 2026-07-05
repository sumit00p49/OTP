# OTP Now Telegram Bot

A Telegram bot that integrates with the OTPNOW API to provide temporary phone numbers and OTP verification services for Telegram and WhatsApp.

## Features

- **Balance Check** — View your current account balance
- **Telegram Numbers** — Get temporary numbers for Telegram verification
- **WhatsApp Numbers (Server 1)** — Get temporary numbers for WhatsApp verification
- **WhatsApp Numbers (Server 2)** — Alternative server for WhatsApp numbers
- Real-time API integration (no database required)
- Emoji-rich formatted responses
- Comprehensive error handling

## Prerequisites

- Python 3.10+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OTPNOW API key

## Installation

1. **Clone or download the project:**
   ```bash
   cd telegram-otp-bot
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set your `BOT_TOKEN` (from @BotFather).

5. **Run the bot:**
   ```bash
   python bot.py
   ```

## Commands

### Account
| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and command list |
| `/balance` | Check your account balance |

### Telegram Numbers
| Command | Description |
|---------|-------------|
| `/tg_countries` | List available countries |
| `/tg_price [code]` | Check price for a country (e.g., `/tg_price US`) |
| `/tg_order [code]` | Order a number (e.g., `/tg_order US`) |
| `/tg_code [number]` | Get OTP code for an ordered number |

### WhatsApp Numbers (Server 1)
| Command | Description |
|---------|-------------|
| `/wp_countries` | List available countries |
| `/wp_price [code]` | Check price (e.g., `/wp_price IN`) |
| `/wp_order [code]` | Order a number |
| `/wp_status [order_id]` | Check if OTP has been received |
| `/wp_cancel [order_id]` | Cancel order and get refund |

### WhatsApp Numbers (Server 2)
| Command | Description |
|---------|-------------|
| `/wp2_countries` | List available countries |
| `/wp2_price [code]` | Check price |
| `/wp2_order [code]` | Order a number |
| `/wp2_status [order_id]` | Check if OTP has been received |
| `/wp2_cancel [order_id]` | Cancel order and get refund |

## Project Structure

```
telegram-otp-bot/
├── bot.py                          # Main entry point
├── config.py                       # Configuration (env vars)
├── api_client.py                   # Async OTPNOW API client
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── README.md                       # This file
├── handlers/
│   ├── __init__.py
│   ├── start.py                    # /start command
│   ├── balance.py                  # /balance command
│   ├── telegram_service.py         # /tg_* commands
│   ├── whatsapp_service.py         # /wp_* commands
│   └── whatsapp2_service.py        # /wp2_* commands
└── utils/
    ├── __init__.py
    └── formatter.py                # Message formatting utilities
```

## Configuration

All configuration is done via environment variables (or a `.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram Bot API token | *(required)* |
| `API_BASE_URL` | OTPNOW API base URL | `https://otpnowapi.lynkzap.shop` |
| `API_KEY` | OTPNOW API key | *(set in .env)* |

## Error Handling

The bot handles the following error scenarios:
- **Invalid API key** — Shows authentication error
- **Insufficient balance** — Notifies user to top up
- **OTP not ready** — Prompts user to wait and retry
- **Network errors** — Shows connectivity issue message
- **Invalid commands** — Shows usage instructions with examples

## Technical Details

- Built with `python-telegram-bot` v20+ (async)
- Uses `aiohttp` for non-blocking API calls
- HTML parse mode for rich message formatting
- No database — all operations are real-time via API
- Graceful shutdown with API session cleanup

## License

This project is for personal/educational use. Use responsibly and in accordance with the OTPNOW API terms of service.
