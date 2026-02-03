import dramatiq
from telegram import Bot
from loguru import logger
from m3dlp.settings import settings, DOWNLOADS_DIR
from dramatiq.middleware.asyncio import AsyncIO
import os
import shutil
import yt_dlp
from telegram.error import TimedOut
from telegram.constants import ChatAction
from dramatiq.middleware import Middleware
from dramatiq.brokers.redis import RedisBroker
import subprocess

class StartupMiddleware(Middleware):
    def before_worker_boot(self, broker, worker):
        # Delete files and directories in downloads directory on worker boot
        for item in os.listdir(DOWNLOADS_DIR):
            path = os.path.join(DOWNLOADS_DIR, item)
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception as e:
                logger.error(f"Failed to delete {path}: {e}")
        
dramatiq.set_broker(RedisBroker(url=settings.BROKER_URL))
dramatiq.get_broker().add_middleware(AsyncIO())
dramatiq.get_broker().add_middleware(StartupMiddleware())
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

@dramatiq.actor(queue_name="media_download")
async def download_media(url, chat_id, original_msg_id, status_msg_id, is_audio=False):
    # Create a unique directory for this download to avoid filename collisions
    media_id = settings.gen_uuid_hex()
    task_dir = os.path.join(DOWNLOADS_DIR, media_id)
    os.makedirs(task_dir, exist_ok=True)
    
    # Use title in filename; yt-dlp will handle the extension
    output_template = os.path.join(task_dir, "%(title)s.%(ext)s")
    
    cmd = []
    if is_audio:
        cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "-x",
            "--audio-format", "mp3",
            "-o", output_template,
            url
        ]
    else:
        cmd = [
            "yt-dlp",
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mkv",
            "--recode-video", "mp4",
            "--postprocessor-args", "VideoConvertor:-c:v libx264 -c:a aac",
            "-o", output_template,
            url
        ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed: {e}")
        shutil.rmtree(task_dir, ignore_errors=True)
        return
        
    # Locate the downloaded file in the task directory
    final_path = None
    try:
        files = [f for f in os.listdir(task_dir) if not f.endswith('.part') and not f.endswith('.ytdl')]
        if files:
            # Assuming the first non-temp file is the media
            final_path = os.path.join(task_dir, files[0])
    except Exception as e:
        logger.error(f"Error listing files in task dir: {e}")

    if not final_path or not os.path.exists(final_path):
        logger.error("Downloaded file not found.")
        shutil.rmtree(task_dir, ignore_errors=True)
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
    
    # Clean up the task directory
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir, ignore_errors=True)