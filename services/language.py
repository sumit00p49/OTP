"""
Multi-language support: English + Hindi.
Users can switch language. Stored in DB.
"""

from database import get_db

# Default language
DEFAULT_LANG = "en"

STRINGS = {
    "en": {
        "welcome_line": "Buy premium TG accounts instantly!",
        "balance": "Balance",
        "status_active": "✅ Active",
        "buy_btn": "📱 𝐁𝐮𝐲 𝐓𝐞𝐥𝐞𝐠𝐫𝐚𝐦 𝐀𝐜𝐜𝐨𝐮𝐧𝐭",
        "deposit_btn": "💰 𝘿𝙚𝙥𝙤𝙨𝙞𝙩",
        "wallet_btn": "💳 𝙒𝙖𝙡𝙡𝙚𝙩",
        "orders_btn": "📋 𝖮𝗋𝖽𝖾𝗋 𝖧𝗂𝗌𝗍𝗈𝗋𝗒",
        "support_btn": "🆘 𝐒𝐮𝐩𝐩𝐨𝐫𝐭",
        "referral_btn": "🎟️ Referral",
        "dashboard_btn": "📊 Dashboard",
        "lang_btn": "🌐 Language",
        "fresh_accounts": "🟢 Fresh Accounts",
        "select_country": "👇 Select a country:",
        "quantity_prompt": "𝖲𝖾𝗇𝖽 𝖳𝗁𝖾 𝖰𝗎𝖺𝗇𝗍𝗂𝗍𝗒 𝖸𝗈𝗎 𝖶𝖺𝗇𝗍 𝖳𝗈 𝖡𝗎𝗒:",
        "purchase_success": "✅ Purchase Successful!",
        "otp_not_ready": "⏳ OTP Not Ready\n\nCode hasn't arrived yet.",
        "insufficient": "⚠️ Insufficient Balance",
        "out_of_stock": "❌ Out of Stock",
    },
    "hi": {
        "welcome_line": "प्रीमियम TG अकाउंट तुरंत खरीदें!",
        "balance": "बैलेंस",
        "status_active": "✅ सक्रिय",
        "buy_btn": "📱 अकाउंट खरीदें",
        "deposit_btn": "💰 जमा करें",
        "wallet_btn": "💳 वॉलेट",
        "orders_btn": "📋 ऑर्डर",
        "support_btn": "🆘 सहायता",
        "referral_btn": "🎟️ रेफरल",
        "dashboard_btn": "📊 डैशबोर्ड",
        "lang_btn": "🌐 भाषा",
        "fresh_accounts": "🟢 ताज़े अकाउंट",
        "select_country": "👇 देश चुनें:",
        "quantity_prompt": "कितने अकाउंट चाहिए वो नंबर भेजें:",
        "purchase_success": "✅ खरीदारी सफल!",
        "otp_not_ready": "⏳ OTP तैयार नहीं\n\nकोड अभी नहीं आया।",
        "insufficient": "⚠️ बैलेंस कम है",
        "out_of_stock": "❌ स्टॉक में नहीं",
    },
}


async def get_user_lang(user_id: int) -> str:
    """Get user's language preference."""
    db = await get_db()
    try:
        cur = await db.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row and row[0] else DEFAULT_LANG
    except Exception:
        return DEFAULT_LANG


async def set_user_lang(user_id: int, lang: str):
    """Set user's language preference."""
    db = await get_db()
    try:
        await db.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()
    except Exception:
        # Column might not exist yet
        try:
            await db.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'en'")
            await db.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
            await db.commit()
        except Exception:
            pass


def t(key: str, lang: str = "en") -> str:
    """Get translated string."""
    return STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
