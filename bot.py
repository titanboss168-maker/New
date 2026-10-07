import json
import os

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==================================================
# CONFIG
# ==================================================

BOT_TOKEN = "8934609911:AAEmljKQ4s6lDD_nUlw57P0miQTbBMDshEY"

CHANNEL_ID = "@RaxiWin_Jaykesh"

# Apna numeric Telegram User ID yahan daalo
ADMIN_ID = 1966787250

DATA_FILE = "bot_data.json"


# ==================================================
# SAVED DATA
# ==================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"emojis": {}}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {"emojis": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


data = load_data()


# ==================================================
# ADMIN CHECK
# ==================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


# ==================================================
# /START
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            "❌ You are not authorized."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "📝 Create Post",
                callback_data="create"
            )
        ],
        [
            InlineKeyboardButton(
                "✨ Save Emoji",
                callback_data="save_emoji"
            ),
            InlineKeyboardButton(
                "📋 Saved Emojis",
                callback_data="list_emoji"
            )
        ],
    ]

    await update.message.reply_text(
        "🤖 Post Manager\n\n"
        "Choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================================================
# CALLBACK HANDLER
# ==================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    action = query.data

    # --------------------------
    # CREATE POST
    # --------------------------

    if action == "create":

        context.user_data.clear()

        context.user_data["mode"] = "media"
        context.user_data["buttons"] = []

        await query.message.reply_text(
            "📝 Create Post\n\n"
            "Photo, Video ya File bhejo.\n"
            "Caption bhi media ke saath bhej sakte ho."
        )

    # --------------------------
    # SAVE EMOJI
    # --------------------------

    elif action == "save_emoji":

        context.user_data["mode"] = "save_emoji"

        await query.message.reply_text(
            "✨ Ab Telegram Premium Custom Emoji bhejo.\n\n"
            "Main uska Custom Emoji ID detect karunga."
        )

    # --------------------------
    # LIST EMOJIS
    # --------------------------

    elif action == "list_emoji":

        emojis = data.get("emojis", {})

        if not emojis:
            await query.message.reply_text(
                "📋 Abhi koi emoji saved nahi hai."
            )
            return

        text = "✨ Saved Custom Emojis\n\n"

        for name, emoji_id in emojis.items():
            text += f"• {name} → `{emoji_id}`\n"

        await query.message.reply_text(
            text,
            parse_mode="Markdown"
        )

    # --------------------------
    # ADD BUTTON
    # --------------------------

    elif action == "add_button":

        buttons = context.user_data.get("buttons", [])

        if len(buttons) >= 3:
            await query.message.reply_text(
                "⚠️ Maximum 3 buttons allowed."
            )
            return

        context.user_data["mode"] = "button_text"

        number = len(buttons) + 1

        await query.message.reply_text(
            f"🔘 Button {number}\n\n"
            "Button ka text bhejo.\n\n"
            "Example:\n"
            "🎁 GET OFFER"
        )

    # --------------------------
    # PUBLISH
    # --------------------------

    elif action == "publish":

        await publish_post(update, context)


# ==================================================
# MESSAGE HANDLER
# ==================================================

async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    if not is_admin(update.effective_user.id):
        return

    message = update.message

    mode = context.user_data.get("mode")

    # ==================================================
    # SAVE CUSTOM EMOJI
    # ==================================================

    if mode == "save_emoji":

        entities = message.entities or []

        custom_emoji_id = None

        for entity in entities:

            if entity.type == "custom_emoji":

                custom_emoji_id = entity.custom_emoji_id
                break

        if not custom_emoji_id:

            await message.reply_text(
                "❌ Custom emoji detect nahi hua.\n\n"
                "Telegram Premium Custom Emoji directly bhejo."
            )

            return

        context.user_data["emoji_id"] = custom_emoji_id
        context.user_data["mode"] = "emoji_name"

        await message.reply_text(
            "✅ Emoji detect ho gaya!\n\n"
            "Ab iska naam bhejo.\n\n"
            "Example:\n"
            "gift"
        )

        return

    # ==================================================
    # EMOJI NAME
    # ==================================================

    if mode == "emoji_name":

        name = message.text.strip()

        emoji_id = context.user_data.get("emoji_id")

        if not emoji_id:

            await message.reply_text(
                "❌ Emoji ID nahi mila."
            )

            return

        data.setdefault("emojis", {})[name] = emoji_id

        save_data(data)

        context.user_data.clear()

        await message.reply_text(
            f"✅ Custom emoji saved!\n\n"
            f"Name: {name}\n"
            f"ID: `{emoji_id}`",
            parse_mode="Markdown"
        )

        return

    # ==================================================
    # MEDIA
    # ==================================================

    if mode == "media":

        if message.photo:

            context.user_data["media_type"] = "photo"
            context.user_data["file_id"] = (
                message.photo[-1].file_id
            )
            context.user_data["caption"] = (
                message.caption or ""
            )

        elif message.video:

            context.user_data["media_type"] = "video"
            context.user_data["file_id"] = (
                message.video.file_id
            )
            context.user_data["caption"] = (
                message.caption or ""
            )

        elif message.document:

            context.user_data["media_type"] = "document"
            context.user_data["file_id"] = (
                message.document.file_id
            )
            context.user_data["caption"] = (
                message.caption or ""
            )

        else:

            await message.reply_text(
                "❌ Sirf Photo, Video ya File bhejo."
            )

            return

        keyboard = [
            [
                InlineKeyboardButton(
                    "➕ Add Button",
                    callback_data="add_button"
                )
            ],
            [
                InlineKeyboardButton(
                    "🚀 Publish",
                    callback_data="publish"
                )
            ]
        ]

        context.user_data["mode"] = "post_setup"

        await message.reply_text(
            "✅ Media received!\n\n"
            "Ab 0–3 buttons add kar sakte ho.\n"
            "Ya direct Publish kar sakte ho.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ==================================================
    # BUTTON TEXT
    # ==================================================

    if mode == "button_text":

        text = message.text.strip()

        if not text:

            await message.reply_text(
                "❌ Button text empty nahi ho sakta."
            )

            return

        context.user_data["button_text"] = text
        context.user_data["mode"] = "button_url"

        await message.reply_text(
            "🔗 Ab button ka URL bhejo.\n\n"
            "Example:\n"
            "https://example.com"
        )

        return

    # ==================================================
    # BUTTON URL
    # ==================================================

    if mode == "button_url":

        url = message.text.strip()

        if not (
            url.startswith("http://")
            or url.startswith("https://")
            or url.startswith("tg://")
        ):

            await message.reply_text(
                "❌ Valid URL bhejo.\n\n"
                "Example:\n"
                "https://example.com"
            )

            return

        button_text = context.user_data.get(
            "button_text"
        )

        buttons = context.user_data.setdefault(
            "buttons",
            []
        )

        buttons.append({
            "text": button_text,
            "url": url
        })

        context.user_data.pop(
            "button_text",
            None
        )

        context.user_data["mode"] = "post_setup"

        if len(buttons) >= 3:

            await message.reply_text(
                "✅ 3 buttons added!\n\n"
                "Maximum 3 buttons reached.\n"
                "Ab Publish kar sakte ho.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🚀 Publish",
                            callback_data="publish"
                        )
                    ]
                ])
            )

        else:

            await message.reply_text(
                f"✅ Button {len(buttons)} added!",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "➕ Add Another",
                            callback_data="add_button"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🚀 Publish",
                            callback_data="publish"
                        )
                    ]
                ])
            )

        return


# ==================================================
# PUBLISH POST
# ==================================================

async def publish_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    media_type = context.user_data.get(
        "media_type"
    )

    file_id = context.user_data.get(
        "file_id"
    )

    caption = context.user_data.get(
        "caption",
        ""
    )

    buttons = context.user_data.get(
        "buttons",
        []
    )

    if not media_type or not file_id:

        await query.message.reply_text(
            "❌ Pehle Photo, Video ya File bhejo."
        )

        return

    # --------------------------
    # CREATE BUTTONS
    # --------------------------

    keyboard = []

    for button in buttons:

        keyboard.append([
            InlineKeyboardButton(
                text=button["text"],
                url=button["url"]
            )
        ])

    reply_markup = (
        InlineKeyboardMarkup(keyboard)
        if keyboard
        else None
    )

    # --------------------------
    # SEND TO CHANNEL
    # --------------------------

    try:

        if media_type == "photo":

            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=file_id,
                caption=caption,
                reply_markup=reply_markup
            )

        elif media_type == "video":

            await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=file_id,
                caption=caption,
                reply_markup=reply_markup
            )

        elif media_type == "document":

            await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=file_id,
                caption=caption,
                reply_markup=reply_markup
            )

        await query.message.reply_text(
            "✅ Post successfully published!"
        )

        context.user_data.clear()

    except Exception as error:

        await query.message.reply_text(
            f"❌ Publish failed:\n\n{error}"
        )


# ==================================================
# MAIN
# ==================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN empty hai."
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            message_handler
        )
    )

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
