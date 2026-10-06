import os
import json
import asyncio

from telegram import (
    Update,
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@MRBEAN_GAMING"

# Apna Telegram numeric user ID yahan daalo
ADMIN_ID = 1966787250

DATA_FILE = "bot_data.json"

# =========================
# DATA
# =========================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"emojis": {}}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"emojis": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


data = load_data()


# =========================
# ADMIN CHECK
# =========================

def is_admin(user_id):
    return user_id == ADMIN_ID


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized.")
        return

    keyboard = [
        [
            InlineKeyboardButton("📝 Create Post", callback_data="create"),
            InlineKeyboardButton("✨ Save Emoji", callback_data="emoji"),
        ],
        [
            InlineKeyboardButton("📋 Saved Emojis", callback_data="list"),
        ],
    ]

    await update.message.reply_text(
        "🤖 **Post Manager**\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    action = query.data

    # SAVE EMOJI
    if action == "emoji":

        context.user_data["mode"] = "save_emoji"

        await query.message.reply_text(
            "✨ Ab mujhe ek **Premium Custom Emoji** bhejo.\n\n"
            "Main uska custom emoji ID save kar lunga."
        )

    # LIST EMOJIS
    elif action == "list":

        emojis = data.get("emojis", {})

        if not emojis:
            await query.message.reply_text(
                "📋 Abhi koi custom emoji saved nahi hai."
            )
            return

        text = "✨ **Saved Custom Emojis**\n\n"

        for name, emoji_id in emojis.items():
            text += f"• `{name}` → `{emoji_id}`\n"

        await query.message.reply_text(
            text,
            parse_mode="Markdown"
        )

    # CREATE POST
    elif action == "create":

        context.user_data.clear()
        context.user_data["mode"] = "waiting_media"
        context.user_data["buttons"] = []

        await query.message.reply_text(
            "📝 **Create Post**\n\n"
            "Ab mujhe Photo, Video ya File bhejo.\n\n"
            "Uske saath caption bhi bhej sakte ho."
        )


# =========================
# MESSAGE HANDLER
# =========================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user:
        return

    if not is_admin(update.effective_user.id):
        return

    message = update.message
    mode = context.user_data.get("mode")

    # -------------------------
    # SAVE CUSTOM EMOJI
    # -------------------------

    if mode == "save_emoji":

        entities = message.entities or []

        for entity in entities:

            if entity.type == "custom_emoji":

                emoji_id = entity.custom_emoji_id

                context.user_data["last_emoji_id"] = emoji_id

                await message.reply_text(
                    "✨ Emoji mil gaya!\n\n"
                    "Ab iska naam bhejo.\n"
                    "Example: `gift`",
                    parse_mode="Markdown",
                )

                context.user_data["mode"] = "emoji_name"
                return

        await message.reply_text(
            "❌ Custom emoji detect nahi hua.\n"
            "Telegram ka Premium Custom Emoji directly bhejo."
        )

        return

    # -------------------------
    # EMOJI NAME
    # -------------------------

    if mode == "emoji_name":

        name = message.text.strip()
        emoji_id = context.user_data.get("last_emoji_id")

        if not emoji_id:
            await message.reply_text("❌ Emoji ID missing.")
            return

        data.setdefault("emojis", {})[name] = emoji_id
        save_data(data)

        context.user_data.clear()

        await message.reply_text(
            f"✅ Saved!\n\n"
            f"Name: `{name}`\n"
            f"ID: `{emoji_id}`",
            parse_mode="Markdown",
        )

        return

    # -------------------------
    # MEDIA
    # -------------------------

    if mode == "waiting_media":

        if message.photo:

            context.user_data["type"] = "photo"
            context.user_data["file_id"] = message.photo[-1].file_id
            context.user_data["caption"] = message.caption or ""

        elif message.video:

            context.user_data["type"] = "video"
            context.user_data["file_id"] = message.video.file_id
            context.user_data["caption"] = message.caption or ""

        elif message.document:

            context.user_data["type"] = "document"
            context.user_data["file_id"] = message.document.file_id
            context.user_data["caption"] = message.caption or ""

        else:

            await message.reply_text(
                "❌ Sirf Photo, Video ya File bhejo."
            )
            return

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔘 Add Button",
                    callback_data="add_button"
                )
            ],
            [
                InlineKeyboardButton(
                    "🚀 Publish",
                    callback_data="publish"
                )
            ],
        ]

        await message.reply_text(
            "✅ Media received.\n\n"
            "Ab buttons add karo ya direct Publish karo.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        context.user_data["mode"] = "post_setup"


# =========================
# ADD BUTTON
# =========================

async def add_button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    buttons = context.user_data.get("buttons", [])

    if len(buttons) >= 3:

        await query.message.reply_text(
            "⚠️ Maximum 3 buttons allowed."
        )
        return

    context.user_data["mode"] = "button_text"

    await query.message.reply_text(
        f"🔘 Button {len(buttons) + 1}\n\n"
        "Button ka text bhejo.\n"
        "Example: `🎁 GET OFFER`",
        parse_mode="Markdown",
    )


# =========================
# BUTTON TEXT / URL
# =========================

async def button_text_or_url(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    mode = context.user_data.get("mode")

    if mode == "button_text":

        context.user_data["temp_button_text"] = update.message.text

        context.user_data["mode"] = "button_url"

        await update.message.reply_text(
            "🔗 Ab button ka URL bhejo."
        )

        return

    if mode == "button_url":

        url = update.message.text.strip()
        text = context.user_data.get("temp_button_text")

        buttons = context.user_data.setdefault("buttons", [])

        buttons.append({
            "text": text,
            "url": url
        })

        context.user_data.pop("temp_button_text", None)

        if len(buttons) >= 3:

            await update.message.reply_text(
                "✅ 3 buttons added.\n\n"
                "Ab Publish kar sakte ho."
            )

        else:

            keyboard = [
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
                ],
            ]

            await update.message.reply_text(
                f"✅ Button {len(buttons)} added.\n\n"
                "Aur button add karna hai ya Publish?",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        context.user_data["mode"] = "post_setup"


# =========================
# PUBLISH
# =========================

async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    post_type = context.user_data.get("type")
    file_id = context.user_data.get("file_id")
    caption = context.user_data.get("caption", "")
    buttons = context.user_data.get("buttons", [])

    if not post_type or not file_id:

        await query.message.reply_text(
            "❌ Pehle Photo, Video ya File send karo."
        )
        return

    keyboard = []

    for button in buttons:

        keyboard.append([
            InlineKeyboardButton(
                button["text"],
                url=button["url"]
            )
        ])

    reply_markup = (
        InlineKeyboardMarkup(keyboard)
        if keyboard
        else None
    )

    bot = context.bot

    if post_type == "photo":

        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=file_id,
            caption=caption,
            reply_markup=reply_markup,
        )

    elif post_type == "video":

        await bot.send_video(
            chat_id=CHANNEL_ID,
            video=file_id,
            caption=caption,
            reply_markup=reply_markup,
        )

    elif post_type == "document":

        await bot.send_document(
            chat_id=CHANNEL_ID,
            document=file_id,
            caption=caption,
            reply_markup=reply_markup,
        )

    await query.message.reply_text(
        "✅ **Published successfully!**",
        parse_mode="Markdown",
    )

    context.user_data.clear()


# =========================
# CALLBACK ROUTER
# =========================

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query.data == "add_button":
        await add_button(update, context)

    elif query.data == "publish":
        await publish(update, context)

    else:
        await button_handler(update, context)


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing from Railway Variables."
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(callback_router)
    )

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            message_handler
        )
    )

    print("Bot started...")

    app.run_polling()


if __name__ == "__main__":
    main()
