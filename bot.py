import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = "8934609911:AAEmljKQ4s6lDD_nUlw57P0miQTbBMDshEY"
CHANNEL_ID = "@MRBEAN_GAMING"

BUTTON_TEXT = "🎁 𝐆𝐈𝐅𝐓 𝐂𝐎𝐃𝐄"
BUTTON_URL = "https://t.me/+sbu2FCVFGshjOTg1"

POST_TEXT = """
🔥 Special Offer

Check out the offer below 👇
"""


async def main():
    async with Bot(token=BOT_TOKEN) as bot:

        button = InlineKeyboardButton(
            text=BUTTON_TEXT,
            url=BUTTON_URL
        )

        keyboard = InlineKeyboardMarkup([
            [button]
        ])

        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=POST_TEXT,
            reply_markup=keyboard
        )


if __name__ == "__main__":
    asyncio.run(main())
