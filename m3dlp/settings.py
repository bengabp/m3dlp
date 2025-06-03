import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import cached_property
import redis
import uuid
import re
from urllib.parse import urlparse

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    BROKER_URL: str = "redis://localhost:6379/0"
    
    model_config = SettingsConfigDict(env_file=".env", extra='ignore', populate_by_name=True)

    @cached_property
    def BASE_DIR(self) -> str:
        """ Returns the base directory of the project """
        return Path(__file__).resolve().parent.parent
    
    @property
    def redis_client(self):
        return redis.Redis(
            host=self.RC_HOST,
            port=self.RC_PORT,
            password=self.RC_PASSWORD,
            username=self.RC_USERNAME,
            db=self.RC_DB, decode_responses=True
        )
    def create_dir(self, *name):
        """For creating recursive and non-recursive directories ."""
        fullpath = os.path.join(self.BASE_DIR, *name)
        os.makedirs(fullpath, exist_ok=True)
        return fullpath

    def gen_uuid_hex(self) -> str:
        return uuid.uuid4().hex
    
    def validate_and_extract_base_url(self, url):
        pattern = re.compile(r'^(https?:\/\/)?([\w\-]+\.)+[\w\-]+(\/[\w\-._~:\/?#[\]@!$&\'()*+,;=]*)?$')
        if pattern.match(url):
            parsed = urlparse(url)
            return parsed.netloc
        return None
    
settings = Settings()
DOWNLOADS_DIR = settings.create_dir("downloads")