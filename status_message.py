"""
Status message with custom emoji support.
"""


async def send_status_message(update):
    """Send a status message with a custom emoji entity."""
    await update.message.reply_text(
        text="Status: 🔘 Active",
        entities=[
            {
                "type": "custom_emoji",
                "offset": 8,
                "length": 1,
                "custom_emoji_id": "6030445631921721471"
            }
        ]
    )
