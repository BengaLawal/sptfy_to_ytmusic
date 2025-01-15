import os
from .base import BaseConfig


class YTMusicConfig(BaseConfig):
    """YouTube Music specific configuration settings."""
    SERVICE_PREFIX = "ytmusic"
    SECRET_NAME = "YtMusic"

    def __init__(self):
        super().__init__()
        self.REDIRECT_URI = os.getenv(
            'YTMUSIC_REDIRECT_URI',
            "http://localhost:5173/ytmusic/callback"
        )