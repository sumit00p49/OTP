# 🛒 Telegram Shop Bot — LZT Market + INR Wallet

A Telegram bot for selling Telegram accounts via the LZT Market API with a built-in INR wallet system. Users deposit INR via UPI, admin approves, and users spend their balance to buy accounts.

## ✨ Features

- **💰 INR Wallet System** — Deposit via UPI, admin-verified
- **📱 Buy TG Accounts** — Direct integration with LZT Market API
- **📋 Order History** — Track all purchases with full details
- **🔐 Admin Panel** — Approve/reject deposits with inline buttons
- **🎨 Rich UI** — Emoji-rich, clean inline keyboard interface
- **⚡ Real-time** — Instant balance updates and account delivery

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/surojbera1000/OTP.git
cd OTP
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
BOT_TOKEN=your_bot_token_from_botfather
LZT_API_KEY=your_lzt_market_api_key
ADMIN_IDS=your_telegram_user_id
ADMIN_GROUP_ID=your_admin_group_id
```

### 3. Run

```bash
python bot.py
```

## 📋 Commands & Flow

### User Commands
| Button | Action |
|--------|--------|
| 📱 Buy TG Accounts | Browse & purchase accounts |
| 💰 Deposit Funds | Add balance via UPI |
| 💳 My Balance | Check wallet balance |
| 📋 My Orders | View purchase history |
| 🆘 Support | Get help |

### Deposit Flow
1. User clicks "Deposit Funds"
2. Bot shows UPI details
3. User clicks "Make Deposit" → enters amount
4. User uploads payment screenshot
5. Bot forwards to admin group with Approve/Reject buttons
6. Admin approves → wallet credited instantly

### Purchase Flow
1. User selects quality (Cheap / Good)
2. User selects country
3. Bot checks balance
4. Bot calls LZT API to buy account
5. Account details shown to user
6. Order saved to history

## 🗄️ Database Schema

### users
| Column | Type | Description |
|--------|------|-------------|
| user_id | INTEGER PK | Telegram user ID |
| username | TEXT | Telegram username |
| first_name | TEXT | User's first name |
| wallet_balance | REAL | Current INR balance |
| created_at | TIMESTAMP | Registration date |

### deposits
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment ID |
| user_id | INTEGER FK | Depositor's user ID |
| amount | REAL | Deposit amount (INR) |
| screenshot_file_id | TEXT | Telegram file ID |
| status | TEXT | PENDING/APPROVED/REJECTED |
| admin_id | INTEGER | Admin who processed |
| created_at | TIMESTAMP | Submission time |

### orders
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment ID |
| order_id | TEXT UNIQUE | Custom order ID |
| user_id | INTEGER FK | Buyer's user ID |
| lzt_item_id | TEXT | LZT Market item ID |
| amount_paid | REAL | Price paid (INR) |
| account_data | TEXT (JSON) | Full account details |
| quality | TEXT | cheap/good |
| country | TEXT | Country code |
| created_at | TIMESTAMP | Purchase time |


## 🏗️ Project Structure

```
OTP/
├── bot.py                    # Main entry point
├── config.py                 # Environment configuration
├── database.py               # SQLite setup & schema
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── handlers/
│   ├── start.py              # /start & main menu
│   ├── deposit.py            # Deposit FSM flow
│   ├── admin.py              # Admin approve/reject
│   ├── shop.py               # Shop & purchase flow
│   ├── orders.py             # Order history
│   ├── balance.py            # Balance check
│   └── support.py            # Support info
├── services/
│   ├── wallet.py             # Wallet operations
│   ├── lzt_api.py            # LZT Market API client
│   └── order_service.py      # Order management
├── keyboards/
│   └── inline.py             # All inline keyboards
├── states/
│   └── deposit_states.py     # FSM states
├── middlewares/
│   └── user_middleware.py    # Auto-register users
└── utils/
    └── formatters.py         # Message formatting
```

## ⚙️ Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram Bot API token | ✅ |
| `LZT_API_KEY` | LZT Market API key | ✅ |
| `ADMIN_IDS` | Comma-separated admin user IDs | ✅ |
| `ADMIN_GROUP_ID` | Group ID for deposit notifications | ✅ |
| `UPI_ID` | UPI payment address | ✅ |
| `UPI_NAME` | Name shown on UPI | ✅ |
| `CHEAP_ACC_PRICE` | Price for cheap accounts (INR) | Default: 30 |
| `GOOD_ACC_PRICE` | Price for good accounts (INR) | Default: 60 |
| `MIN_DEPOSIT` | Minimum deposit amount | Default: 10 |
| `DB_PATH` | SQLite database file path | Default: bot_database.db |
| `LZT_CATEGORY` | LZT category slug | Default: telegram |

## 🔒 Security

- Admin approval is restricted by Telegram user ID
- Wallet debits use atomic database transactions
- Failed purchases trigger automatic refunds
- Screenshots are stored as Telegram file IDs (not locally)

## 🚀 Deployment (VPS)

```bash
# Using screen
screen -S shopbot
python bot.py
# Ctrl+A, D to detach

# Using systemd
sudo nano /etc/systemd/system/shopbot.service
sudo systemctl enable shopbot
sudo systemctl start shopbot
```

## 📝 License

For personal/educational use. Use responsibly.
