from loguru import logger
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from m3dlp.settings import settings
from m3dlp.tasks import download_media


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_text= "Invalid URL!"
    text = update.message.text.strip()
    msg_id = update.message.message_id
    
    is_audio = False
    if text.lower().startswith("audio "):
        is_audio = True
        text = text[6:].strip()
    elif text.lower().endswith(" audio"):
        is_audio = True
        text = text[:-6].strip()

    if settings.validate_and_extract_base_url(text):
        msg = await update.message.reply_text("Download started!", reply_to_message_id=msg_id)
        logger.info(f"MSG: {text} | Audio: {is_audio}")
        download_media.send(text, update.effective_chat.id, msg_id, msg.message_id, is_audio)
    else:
        await update.message.reply_text(reply_text, reply_to_message_id=msg_id)


def main() -> None:
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    logger.info("Starting the bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()