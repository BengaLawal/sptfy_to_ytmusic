import os


class BaseConfig:
    """Base configuration class with common settings."""
    REGION_NAME = "eu-west-1"

    def __init__(self):
        self.USERS_TABLE = os.getenv('USERS_TABLE', "dev-UsersTable")
        self.TRANSFER_TABLE = os.getenv('TRANSFER_DETAILS_TABLE', "dev-TransferDetailsTable")
        self.ACCESS_CONTROL_ALLOW_ORIGIN = os.getenv('ACCESS_CONTROL_ALLOW_ORIGIN', 'http://localhost:5173')