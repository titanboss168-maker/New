import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

BUTTON_TEXT = "🎁 𝐆𝐈𝐅𝐓 𝐂𝐎𝐃𝐄"
BUTTON_URL = "https://t.me/+sbu2FCVFGshjOTg1"

POST_TEXT = """
🔥 Special Offer

Check out the offer below 👇
"""

def main():
    bot = Bot(token=BOT_TOKEN)

    button = InlineKeyboardButton(
        text=BUTTON_TEXT,
        url=BUTTON_URL
    )

    keyboard = InlineKeyboardMarkup([
        [button]
    ])

    bot.send_message(
        chat_id=CHANNEL_ID,
        text=POST_TEXT,
        reply_markup=keyboard
    )

if __name__ == "__main__":
    main()
