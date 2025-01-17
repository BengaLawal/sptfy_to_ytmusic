import unittest
import os
from unittest.mock import patch
from config.base import BaseConfig
from config import SpotifyConfig, YTMusicConfig, AuthorizerConfig


class TestBaseConfig(unittest.TestCase):
    def setUp(self):
        # Reset environment variables before each test
        self.env_vars = {
            'USERS_TABLE': None,
            'ACCESS_CONTROL_ALLOW_ORIGIN': None
        }
        self.original_env = {}
        for key in self.env_vars:
            if key in os.environ:
                self.original_env[key] = os.environ[key]
                del os.environ[key]

    def tearDown(self):
        # Restore original environment variables
        for key in self.env_vars:
            if key in self.original_env:
                os.environ[key] = self.original_env[key]
            elif key in os.environ:
                del os.environ[key]

    def test_default_values(self):
        config = BaseConfig()
        self.assertEqual(config.REGION_NAME, "eu-west-1")
        self.assertEqual(config.USERS_TABLE, "dev-UsersTable")
        self.assertTrue(
            config.ACCESS_CONTROL_ALLOW_ORIGIN in
            ["https://master.d3tjriompcjyyz.amplifyapp.com", "http://localhost:5173"]
        )

    def test_environment_override(self):
        test_values = {
            'USERS_TABLE': 'prod-table',
            'ACCESS_CONTROL_ALLOW_ORIGIN': 'https://prod.example.com'
        }
        with patch.dict(os.environ, test_values):
            config = BaseConfig()
            self.assertEqual(config.USERS_TABLE, 'prod-table')
            self.assertEqual(
                config.ACCESS_CONTROL_ALLOW_ORIGIN,
                'https://prod.example.com'
            )


class TestSpotifyConfig(unittest.TestCase):
    def setUp(self):
        if 'SPOTIFY_REDIRECT_URI' in os.environ:
            self.original_redirect_uri = os.environ['SPOTIFY_REDIRECT_URI']
            del os.environ['SPOTIFY_REDIRECT_URI']
        else:
            self.original_redirect_uri = None

    def tearDown(self):
        if self.original_redirect_uri is not None:
            os.environ['SPOTIFY_REDIRECT_URI'] = self.original_redirect_uri
        elif 'SPOTIFY_REDIRECT_URI' in os.environ:
            del os.environ['SPOTIFY_REDIRECT_URI']

    def test_default_values(self):
        config = SpotifyConfig()
        self.assertEqual(config.SERVICE_PREFIX, "spotify")
        self.assertEqual(config.SECRET_NAME, "Spotify")
        self.assertEqual(
            config.SCOPE,
            "user-read-email, user-read-private, playlist-read-private, "
            "playlist-read-collaborative, user-library-read"
        )
        self.assertTrue(
            config.REDIRECT_URI in [
                "https://master.d3tjriompcjyyz.amplifyapp.com/spotify/callback",
                "http://localhost:5173/spotify/callback"
            ]
        )
        # Test inheritance
        self.assertEqual(config.REGION_NAME, "eu-west-1")

    def test_redirect_uri_override(self):
        test_uri = "https://test.example.com/callback"
        with patch.dict(os.environ, {'SPOTIFY_REDIRECT_URI': test_uri}):
            config = SpotifyConfig()
            self.assertEqual(config.REDIRECT_URI, test_uri)


class TestYTMusicConfig(unittest.TestCase):
    def setUp(self):
        if 'YTMUSIC_REDIRECT_URI' in os.environ:
            self.original_redirect_uri = os.environ['YTMUSIC_REDIRECT_URI']
            del os.environ['YTMUSIC_REDIRECT_URI']
        else:
            self.original_redirect_uri = None

    def tearDown(self):
        if self.original_redirect_uri is not None:
            os.environ['YTMUSIC_REDIRECT_URI'] = self.original_redirect_uri
        elif 'YTMUSIC_REDIRECT_URI' in os.environ:
            del os.environ['YTMUSIC_REDIRECT_URI']

    def test_default_values(self):
        config = YTMusicConfig()
        self.assertEqual(config.SERVICE_PREFIX, "ytmusic")
        self.assertEqual(config.SECRET_NAME, "YtMusic")
        self.assertEqual(
            config.REDIRECT_URI,
            "http://localhost:5173/ytmusic/callback"
        )
        # Test inheritance
        self.assertEqual(config.REGION_NAME, "eu-west-1")

    def test_redirect_uri_override(self):
        test_uri = "http://test.local/callback"
        with patch.dict(os.environ, {'YTMUSIC_REDIRECT_URI': test_uri}):
            config = YTMusicConfig()
            self.assertEqual(config.REDIRECT_URI, test_uri)


class TestAuthorizerConfig(unittest.TestCase):
    def setUp(self):
        # Reset environment variables before each test
        self.env_vars = {
            'PLAYLIST_TRANSFER_TOPIC': None,
            'USER_POOL_ID': None,
            'APPLICATION_CLIENT_ID': None,
            'ADMIN_GROUP_NAME': None
        }
        self.original_env = {}
        for key in self.env_vars:
            if key in os.environ:
                self.original_env[key] = os.environ[key]
                del os.environ[key]

    def tearDown(self):
        # Restore original environment variables
        for key in self.env_vars:
            if key in self.original_env:
                os.environ[key] = self.original_env[key]
            elif key in os.environ:
                del os.environ[key]

    def test_default_values(self):
        config = AuthorizerConfig()
        self.assertIsNone(config.PLAYLIST_TRANSFER_TOPIC)
        self.assertIsNone(config.USER_POOL_ID)
        self.assertIsNone(config.APP_CLIENT_ID)
        self.assertIsNone(config.ADMIN_GROUP_NAME)

    def test_environment_override(self):
        test_values = {
            'PLAYLIST_TRANSFER_TOPIC': 'test-topic',
            'USER_POOL_ID': 'test-user-pool-id',
            'APPLICATION_CLIENT_ID': 'test-app-client-id',
            'ADMIN_GROUP_NAME': 'test-admin-group'
        }
        with patch.dict(os.environ, test_values):
            config = AuthorizerConfig()
            self.assertEqual(config.PLAYLIST_TRANSFER_TOPIC, 'test-topic')
            self.assertEqual(config.USER_POOL_ID, 'test-user-pool-id')
            self.assertEqual(config.APP_CLIENT_ID, 'test-app-client-id')
            self.assertEqual(config.ADMIN_GROUP_NAME, 'test-admin-group')


if __name__ == '__main__':
    unittest.main()