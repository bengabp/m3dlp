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
async def download_media(url, chat_id, original_msg_id, status_msg_id, is_audio=False):
    # try:
    media_id = settings.gen_uuid_hex()
    
    if is_audio:
        # Use template to preserve title in filename, prefixed with ID for uniqueness
        output_template = os.path.join(DOWNLOADS_DIR, f"{media_id}_%(title)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "-x",
            "--audio-format", "mp3",
            "-o", output_template,
            url
        ]
    else:
        video_path = os.path.join(DOWNLOADS_DIR, f"{media_id}.mp4")
        cmd = [
            "yt-dlp",
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mkv",
            "--recode-video", "mp4",
            "--postprocessor-args", "VideoConvertor:-c:v libx264 -c:a aac",
            "-o", video_path,
            url
        ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed: {e}")
        return
        
    # Locate the downloaded file
    final_path = None
    if is_audio:
        # Find file starting with media_id in downloads dir
        for f in os.listdir(DOWNLOADS_DIR):
            if f.startswith(media_id):
                final_path = os.path.join(DOWNLOADS_DIR, f)
                break
    else:
        final_path = video_path

    if not final_path or not os.path.exists(final_path):
        logger.error("Downloaded file not found.")
        return

    while 1:
        try:
            with open(final_path, "rb") as media_file:
                # Delete the "Download started!" message
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
                except Exception as e:
                    logger.warning(f"Failed to delete status message: {e}")

                if is_audio:
                    await bot.send_audio(
                        chat_id=chat_id, 
                        audio=media_file, 
                        reply_to_message_id=original_msg_id, 
                        read_timeout=200,
                        write_timeout=200,
                        pool_timeout=200,
                        connect_timeout=200
                    )
                else:
                    await bot.send_video(
                        chat_id=chat_id, 
                        video=media_file, 
                        reply_to_message_id=original_msg_id, 
                        supports_streaming=True,
                        read_timeout=200,
                        write_timeout=200,
                        pool_timeout=200,
                        connect_timeout=200
                    )
            break
        except TimedOut:
            logger.warning("Timed out while sending media, retrying...")
            continue
    
    if os.path.exists(final_path):
        os.remove(final_path)

    # except Exception as e:
    #     logger.error(f"Error downloading video: {e}")
    #     await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Failed to download video.")