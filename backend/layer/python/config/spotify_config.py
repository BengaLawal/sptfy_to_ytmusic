import os
from .base import BaseConfig


class SpotifyConfig(BaseConfig):
    """Spotify-specific configuration settings."""
    SERVICE_PREFIX = "spotify"
    SECRET_NAME = "Spotify"
    SCOPE = (
        "user-read-email, user-read-private, playlist-read-private, "
        "playlist-read-collaborative, user-library-read"
    )

    def __init__(self):
        super().__init__()
        self.REDIRECT_URI = os.getenv(
            'SPOTIFY_REDIRECT_URI',
            "https://master.d3tjriompcjyyz.amplifyapp.com/spotify/callback"
        )
