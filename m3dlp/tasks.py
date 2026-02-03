import dramatiq
from telegram import Bot
from loguru import logger
from m3dlp.settings import settings, DOWNLOADS_DIR
from dramatiq.middleware.asyncio import AsyncIO
import os
import yt_dlp
from telegram.error import TimedOut
from telegram.constants import ChatAction
from dramatiq.middleware import Middleware
from dramatiq.brokers.redis import RedisBroker
import subprocess

class StartupMiddleware(Middleware):
    def before_worker_boot(self, broker, worker):
        # Delete files in downloads directory on worker boot
        for file in map(lambda f: os.path.join(DOWNLOADS_DIR, f), os.listdir(DOWNLOADS_DIR)):
            try:
                if os.path.isfile(file):
                    os.remove(file)
            except Exception as e:
                logger.error(f"Failed to delete {file}: {e}")
        
dramatiq.set_broker(RedisBroker(url=settings.BROKER_URL))
dramatiq.get_broker().add_middleware(AsyncIO())
dramatiq.get_broker().add_middleware(StartupMiddleware())
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

@dramatiq.actor(queue_name="media_download")
async def download_media(url, chat_id, message_id):
    # try:
    media_id = settings.gen_uuid_hex()
    video_path = os.path.join(DOWNLOADS_DIR, f"{media_id}.mp4")
    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "--recode-video", "mp4",
        "--merge-output-format", "mp4",
        "-o", video_path,
        url
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed: {e}")
        return

    while 1:
        try:
            with open(video_path, "rb") as video_file:
                await bot.send_video(
                    chat_id=chat_id, 
                    video=video_file, 
                    reply_to_message_id=message_id, 
                    supports_streaming=True,
                    read_timeout=200,
                    write_timeout=200,
                    pool_timeout=200,
                    connect_timeout=200
                )
            break
        except TimedOut:
            logger.warning("Timed out while sending video, retrying...")
            continue
    os.remove(video_path)

    # except Exception as e:
    #     logger.error(f"Error downloading video: {e}")
    #     await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Failed to download video.")