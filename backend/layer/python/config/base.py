import os


class BaseConfig:
    """Base configuration class with common settings."""
    REGION_NAME = "eu-west-1"

    def __init__(self):
        self.USERS_TABLE = os.getenv('USERS_TABLE', "dev-UsersTable")
        self.ACCESS_CONTROL_ALLOW_ORIGIN = os.getenv(
            'ACCESS_CONTROL_ALLOW_ORIGIN',
            "https://master.d3tjriompcjyyz.amplifyapp.com"
        )