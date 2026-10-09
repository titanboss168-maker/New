import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@MRBEAN_GAMING")

BUTTON_TEXT, BUTTON_URL, CONFIRM = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != ADMIN_ID:
        await update.effective_message.reply_text("Not authorized.")
        return ConversationHandler.END

    await update.effective_message.reply_text(
        "🎬 Send your video with caption.\n"
        "Caption video ke saath bhej sakte ho."
    )
    return BUTTON_TEXT


async def get_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not msg or not msg.video:
        await msg.reply_text("Please send a video with optional caption.")
        return BUTTON_TEXT

    context.user_data["video"] = msg.video.file_id
    context.user_data["caption"] = msg.caption or ""

    await msg.reply_text("✅ Video received!\n\nAb button ka text bhejo:")
    return BUTTON_URL


async def get_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.effective_message.text or "").strip()

    if not text:
        await update.effective_message.reply_text("Button text bhejo.")
        return BUTTON_URL

    context.user_data["button_text"] = text
    await update.effective_message.reply_text(
        "🔗 Ab button ka URL bhejo.\nExample: https://example.com"
    )
    return CONFIRM


async def get_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from urllib.parse import urlparse

    url = (update.effective_message.text or "").strip()
    parsed = urlparse(url)

    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        await update.effective_message.reply_text(
            "❌ Valid URL bhejo, jaise https://example.com"
        )
        return CONFIRM

    context.user_data["button_url"] = url

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            context.user_data["button_text"],
            url=url
        )],
        [InlineKeyboardButton("🚀 PUBLISH", callback_data="publish")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="cancel")],
    ])

    await update.effective_message.reply_text(
        "Ready to publish your video?",
        reply_markup=keyboard,
    )
    return ConversationHandler.END


async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    if query.data == "cancel":
        context.user_data.clear()
        await query.message.reply_text("❌ Cancelled. Send /start to create another post.")
        return

    video = context.user_data.get("video")
    if not video:
        await query.message.reply_text("Video missing. Send /start again.")
        return

    button = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            context.user_data["button_text"],
            url=context.user_data["button_url"],
        )]
    ])

    try:
        await context.bot.send_video(
            chat_id=CHANNEL_ID,
            video=video,
            caption=context.user_data.get("caption", ""),
            reply_markup=button,
        )
        await query.message.reply_text("✅ Video successfully posted to channel!")
        context.user_data.clear()

    except Exception as e:
        print("Publish error:", e)
        await query.message.reply_text(
            "❌ Post failed. Check CHANNEL_ID and bot channel-admin permissions."
        )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text("Cancelled. Send /start to begin again.")
    return ConversationHandler.END


def main():
    if not TOKEN or ADMIN_ID == 0:
        raise RuntimeError("Set BOT_TOKEN and ADMIN_ID in Railway Variables.")

    app = Application.builder().token(TOKEN).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            BUTTON_TEXT: [
                MessageHandler(filters.VIDEO, get_video),
                MessageHandler(filters.ALL & ~filters.COMMAND, get_video),
            ],
            BUTTON_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_button_text)
            ],
            CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_button_url)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )

    app.add_handler(conversation)
    app.add_handler(
        __import__("telegram.ext", fromlist=["CallbackQueryHandler"])
        .CallbackQueryHandler(publish, pattern="^(publish|cancel)$")
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
