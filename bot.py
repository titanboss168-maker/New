import json
import os
from pathlib import Path
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Configure these in Railway -> Service -> Variables.
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "@RaxiWin_Jaykesh").strip()

# Attach a Railway Volume mounted at /data, then keep DATA_DIR=/data.
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
DATA_FILE = DATA_DIR / "bot_data.json"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Add it in Railway Variables.")

if not ADMIN_ID_RAW.isdigit() or int(ADMIN_ID_RAW) <= 0:
    raise RuntimeError("ADMIN_ID must be your numeric Telegram user ID.")

ADMIN_ID = int(ADMIN_ID_RAW)


# -------------------- Persistent data --------------------

def load_data():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            with DATA_FILE.open("r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                saved.setdefault("emojis", {})
                return saved
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not load saved data: {exc}")
    return {"emojis": {}}


def save_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = DATA_DIR / "bot_data.tmp"
    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_file, DATA_FILE)


data = load_data()


def is_admin(user_id):
    return user_id == ADMIN_ID


def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Create Post", callback_data="create")],
        [
            InlineKeyboardButton("✨ Save Emoji", callback_data="save_emoji"),
            InlineKeyboardButton("📋 Saved Emojis", callback_data="list_emoji"),
        ],
    ])


# -------------------- Commands --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    if not is_admin(user.id):
        await message.reply_text("❌ You are not authorized.")
        return

    await message.reply_text(
        "🤖 Post Manager\n\nChoose an option:",
        reply_markup=main_keyboard(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    context.user_data.clear()
    await update.effective_message.reply_text(
        "Cancelled. Send /start to open the menu again."
    )


# -------------------- Buttons --------------------

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    action = query.data

    if action == "create":
        context.user_data.clear()
        context.user_data["mode"] = "media"
        context.user_data["buttons"] = []
        await query.message.reply_text(
            "📝 Create Post\n\n"
            "Send a photo, video, or document/file.\n"
            "You can include a caption with the media."
        )

    elif action == "save_emoji":
        context.user_data["mode"] = "save_emoji"
        await query.message.reply_text(
            "✨ Send one Telegram Premium custom emoji directly in a message."
        )

    elif action == "list_emoji":
        emojis = data.get("emojis", {})
        if not emojis:
            await query.message.reply_text("📋 No emojis saved yet.")
            return
        lines = ["✨ Saved Custom Emojis", ""]
        for name, emoji_id in emojis.items():
            lines.append(f"• {name} → {emoji_id}")
        await query.message.reply_text("\n".join(lines))

    elif action == "add_button":
        buttons = context.user_data.get("buttons", [])
        if len(buttons) >= 3:
            await query.message.reply_text("⚠️ Maximum 3 buttons allowed.")
            return
        if context.user_data.get("mode") not in ("post_setup", "button_text"):
            await query.message.reply_text("Start with Create Post first.")
            return
        context.user_data["mode"] = "button_text"
        await query.message.reply_text(
            f"🔘 Button {len(buttons) + 1}\n\n"
            "Send the button text, e.g. 🎁 GET OFFER"
        )

    elif action == "publish":
        await publish_post(update, context)

    elif action == "cancel":
        context.user_data.clear()
        await query.message.reply_text(
            "Cancelled. Send /start to open the menu again."
        )


# -------------------- Message workflow --------------------

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not is_admin(user.id):
        return

    mode = context.user_data.get("mode")

    # Save a Telegram Premium custom emoji ID.
    if mode == "save_emoji":
        entities = message.entities or []
        custom_emoji_id = next(
            (
                entity.custom_emoji_id
                for entity in entities
                if entity.type == "custom_emoji"
            ),
            None,
        )
        if not custom_emoji_id:
            await message.reply_text(
                "❌ Custom emoji not detected. Send a Telegram Premium custom emoji directly."
            )
            return

        context.user_data["emoji_id"] = custom_emoji_id
        context.user_data["mode"] = "emoji_name"
        await message.reply_text(
            "✅ Emoji detected!\nNow send a short name for it, e.g. gift"
        )
        return

    if mode == "emoji_name":
        name = (message.text or "").strip()
        emoji_id = context.user_data.get("emoji_id")
        if not name or not emoji_id:
            await message.reply_text("❌ Send a non-empty emoji name.")
            return

        data.setdefault("emojis", {})[name] = emoji_id
        try:
            save_data()
        except OSError as exc:
            # Roll back the in-memory change if persistence fails.
            data["emojis"].pop(name, None)
            await message.reply_text(
                f"❌ Could not save data: {exc}\n"
                "Check that a Railway Volume is mounted at DATA_DIR."
            )
            return

        context.user_data.clear()
        await message.reply_text(
            f"✅ Custom emoji saved!\nName: {name}\nID: {emoji_id}"
        )
        return

    # Receive the media for a channel post.
    if mode == "media":
        if message.photo:
            media_type, file_id = "photo", message.photo[-1].file_id
        elif message.video:
            media_type, file_id = "video", message.video.file_id
        elif message.document:
            media_type, file_id = "document", message.document.file_id
        else:
            await message.reply_text("❌ Send a photo, video, or document/file.")
            return

        context.user_data["media_type"] = media_type
        context.user_data["file_id"] = file_id
        context.user_data["caption"] = message.caption or ""
        context.user_data["mode"] = "post_setup"

        await message.reply_text(
            "✅ Media received!\n\nAdd 0–3 URL buttons, or publish now.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Button", callback_data="add_button")],
                [InlineKeyboardButton("🚀 Publish", callback_data="publish")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
            ]),
        )
        return

    # Receive a button label.
    if mode == "button_text":
        text = (message.text or "").strip()
        if not text:
            await message.reply_text("❌ Button text cannot be empty. Try again.")
            return

        context.user_data["button_text"] = text
        context.user_data["mode"] = "button_url"
        await message.reply_text(
            "🔗 Now send the button URL.\nExample: https://example.com"
        )
        return

    # Receive and validate a button URL.
    if mode == "button_url":
        url = (message.text or "").strip()
        parsed = urlparse(url)

        if parsed.scheme not in ("https", "http", "tg") or (
            parsed.scheme in ("https", "http") and not parsed.netloc
        ):
            await message.reply_text(
                "❌ Invalid URL. Send a URL starting with https:// or http://."
            )
            return

        button_text = context.user_data.pop("button_text", "Open")
        buttons = context.user_data.setdefault("buttons", [])
        if len(buttons) >= 3:
            context.user_data["mode"] = "post_setup"
            await message.reply_text("⚠️ Maximum 3 buttons allowed.")
            return

        buttons.append({"text": button_text, "url": url})
        context.user_data["mode"] = "post_setup"

        keyboard = []
        if len(buttons) < 3:
            keyboard.append([
                InlineKeyboardButton("➕ Add Another", callback_data="add_button")
            ])
        keyboard.append([
            InlineKeyboardButton("🚀 Publish", callback_data="publish")
        ])
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ])

        await message.reply_text(
            f"✅ Button {len(buttons)} added!\n"
            f"You have {3 - len(buttons)} button slot(s) left.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# -------------------- Publish to channel --------------------

async def publish_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    media_type = context.user_data.get("media_type")
    file_id = context.user_data.get("file_id")
    caption = context.user_data.get("caption", "")
    buttons = context.user_data.get("buttons", [])

    if not media_type or not file_id:
        await query.message.reply_text("❌ Create a post and send media first.")
        return

    keyboard = [
        [InlineKeyboardButton(text=item["text"], url=item["url"])]
        for item in buttons
    ]
    markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    try:
        if media_type == "photo":
            await context.bot.send_photo(
                chat_id=CHANNEL_ID, photo=file_id,
                caption=caption, reply_markup=markup,
            )
        elif media_type == "video":
            await context.bot.send_video(
                chat_id=CHANNEL_ID, video=file_id,
                caption=caption, reply_markup=markup,
            )
        elif media_type == "document":
            await context.bot.send_document(
                chat_id=CHANNEL_ID, document=file_id,
                caption=caption, reply_markup=markup,
            )

        await query.message.reply_text("✅ Post successfully published!")
        context.user_data.clear()

    except Exception as exc:
        print(f"Publish error: {exc}")
        await query.message.reply_text(
            "❌ Publish failed. Check that the bot is an administrator "
            "of the channel and has permission to post."
        )


# -------------------- Start bot --------------------

def main():
    if not CHANNEL_ID:
        raise RuntimeError("Set CHANNEL_ID in Railway Variables.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, message_handler)
    )

    print("Bot is starting with polling. Run only ONE active instance.")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
