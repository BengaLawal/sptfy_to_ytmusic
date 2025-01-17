import os
from .base import BaseConfig


class AuthorizerConfig(BaseConfig):
    """Authorizer-specific configuration settings."""
    def __init__(self):
        super().__init__()
        self.PLAYLIST_TRANSFER_TOPIC = os.getenv('PLAYLIST_TRANSFER_TOPIC', None )
        self.USER_POOL_ID = os.getenv('USER_POOL_ID', None)
        self.APP_CLIENT_ID = os.getenv('APPLICATION_CLIENT_ID', None)
        self.ADMIN_GROUP_NAME = os.getenv('ADMIN_GROUP_NAME', None)