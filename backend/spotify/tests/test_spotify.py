import os
import unittest
import boto3
import spotipy
from moto import mock_aws
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, ANY, call

from backend.spotify.src.api.spotify import (
    _get_spotify_service, _refresh_spotify_token, _exchange_code_for_token,
    _get_playlists
)
from backend.layer.python.config.spotify_config import SpotifyConfig

config_ = SpotifyConfig()

def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


def _mock_dynamodb_table():
    """Helper function to create a mock DynamoDB table."""
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.create_table(
        TableName='dev-UsersTable',
        KeySchema=[{'AttributeName': 'userid', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'userid', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
    )
    return table


class TestSpotifyHelpers(unittest.TestCase):
    """Test class for Spotify helper functions."""

    def setUp(self):
        aws_credentials()
        self.user_id = "test_user_123"
        self.current_time = int(datetime.now(timezone.utc).timestamp())
        self.access_token = "test_access_token"
        self.refresh_token = "test_refresh_token"
        self.token_info = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_in': 3600,
            'token_type': 'Bearer',
            'expires_at': int(datetime.now(timezone.utc).timestamp()) + 3600
        }
        self.mock_secrets = {
            "SPOTIPY_CLIENT_ID": "test_client_id",
            "SPOTIPY_CLIENT_SECRET": "test_client_secret"
        }
        self.logger = MagicMock()

    def tearDown(self):
        for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SECURITY_TOKEN",
                    "AWS_SESSION_TOKEN", "AWS_DEFAULT_REGION"]:
            os.environ.pop(key, None)

    @mock_aws
    def test_get_spotify_service_success(self):
        """Test successful creation of Spotify service."""
        with patch('backend.spotify.src.api.spotify.get_secret', return_value=self.mock_secrets), \
                patch('backend.spotify.src.api.spotify.SpotifyOAuth') as mock_oauth, \
                patch('backend.spotify.src.api.spotify.spotipy.Spotify') as mock_spotify_class:
            mock_spotify = MagicMock()
            mock_spotify_class.return_value = mock_spotify

            result = _get_spotify_service()

            mock_oauth.assert_called_once_with(
                client_id=self.mock_secrets["SPOTIPY_CLIENT_ID"],
                client_secret=self.mock_secrets["SPOTIPY_CLIENT_SECRET"],
                redirect_uri=config_.REDIRECT_URI,
                scope=config_.SCOPE,
                open_browser=True,
                show_dialog=True,
                cache_handler=ANY
            )
            self.assertEqual(result, mock_spotify)

    @mock_aws
    def test_get_spotify_service_missing_secrets(self):
        """Test handling of missing secrets."""
        incomplete_secrets = {"SPOTIPY_CLIENT_ID": "test_id"}

        with patch('backend.spotify.src.api.spotify.get_secret', return_value=incomplete_secrets), \
                patch('backend.spotify.src.api.spotify.logger', self.logger):
            with self.assertRaises(KeyError):
                _get_spotify_service()

    @mock_aws
    def test_refresh_spotify_token_success(self):
        """Test successful token refresh."""
        table = _mock_dynamodb_table()
        table.put_item(Item={'userid': self.user_id})

        new_token_info = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600
        }

        mock_spotify = MagicMock()
        mock_spotify.auth_manager.refresh_access_token.return_value = new_token_info

        with patch('backend.spotify.src.api.spotify._get_spotify_service', return_value=mock_spotify), \
                patch('backend.spotify.src.api.spotify.db_service.update_token', return_value=True):
            result = _refresh_spotify_token(self.user_id, self.refresh_token)

            self.assertEqual(result, new_token_info['access_token'])
            mock_spotify.auth_manager.refresh_access_token.assert_called_once_with(self.refresh_token)

    @mock_aws
    def test_refresh_spotify_token_update_failure(self):
        """Test token refresh with database update failure."""
        mock_spotify = MagicMock()
        mock_spotify.auth_manager.refresh_access_token.return_value = self.token_info

        with patch('backend.spotify.src.api.spotify._get_spotify_service', return_value=mock_spotify), \
                patch('backend.spotify.src.api.spotify.db_service.update_token', return_value=False):
            result = _refresh_spotify_token(self.user_id, self.refresh_token)

            self.assertIsNone(result)

    def test_exchange_code_for_token_success(self):
        """Test successful code exchange for token."""
        mock_auth_manager = MagicMock()
        mock_auth_manager.get_cached_token.return_value = self.token_info

        mock_spotify = MagicMock()
        mock_spotify.auth_manager = mock_auth_manager

        with patch('backend.spotify.src.api.spotify._get_spotify_service', return_value=mock_spotify):
            result = _exchange_code_for_token("test_code")

            self.assertEqual(result, self.token_info)
            mock_auth_manager.get_access_token.assert_called_once_with(
                code="test_code",
                as_dict=False,
                check_cache=True
            )

    def test_exchange_code_for_token_failure(self):
        """Test failed code exchange."""
        mock_auth_manager = MagicMock()
        mock_auth_manager.get_access_token.side_effect = spotipy.SpotifyOauthError("error")

        mock_spotify = MagicMock()
        mock_spotify.auth_manager = mock_auth_manager

        with patch('backend.spotify.src.api.spotify._get_spotify_service', return_value=mock_spotify), \
                patch('backend.spotify.src.api.spotify.logger', self.logger):
            result = _exchange_code_for_token("invalid_code")

            self.assertIsNone(result)
            self.logger.error.assert_called()

    def test_get_playlists_single_page(self):
        """Test playlist retrieval with single page."""
        mock_response = {
            'items': [{'id': 'playlist1', 'name': 'Test Playlist'}],
            'next': None
        }

        mock_spotify = MagicMock()
        mock_spotify.current_user_playlists.return_value = mock_response

        with patch('backend.spotify.src.api.spotify.spotipy.Spotify', return_value=mock_spotify):
            result = _get_playlists(self.access_token)

            self.assertIsNotNone(result)
            self.assertEqual(len(result['items']), 1)
            self.assertEqual(result['total'], 1)
            mock_spotify.current_user_playlists.assert_called_once_with(limit=50, offset=0)

    def test_get_playlists_multiple_pages(self):
        """Test playlist retrieval with multiple pages."""
        responses = [
            {'items': [{'id': f'playlist{i}'} for i in range(50)], 'next': 'next_url'},
            {'items': [{'id': f'playlist{i}'} for i in range(50, 75)], 'next': None}
        ]

        mock_spotify = MagicMock()
        mock_spotify.current_user_playlists.side_effect = responses

        with patch('backend.spotify.src.api.spotify.spotipy.Spotify', return_value=mock_spotify):
            result = _get_playlists(self.access_token)

            self.assertEqual(len(result['items']), 75)
            self.assertEqual(result['total'], 75)
            calls = [call(limit=50, offset=0), call(limit=50, offset=50)]
            mock_spotify.current_user_playlists.assert_has_calls(calls)

    def test_get_playlists_error_handling(self):
        """Test playlist retrieval error handling."""
        mock_spotify = MagicMock()
        mock_spotify.current_user_playlists.side_effect = Exception("API Error")

        with patch('backend.spotify.src.api.spotify.spotipy.Spotify', return_value=mock_spotify), \
                patch('backend.spotify.src.api.spotify.logger', self.logger):
            result = _get_playlists(self.access_token)

            self.assertIsNone(result)
            self.logger.error.assert_called_with("Error fetching playlists: API Error")

    def test_get_playlists_invalid_response(self):
        """Test handling of invalid API response."""
        mock_spotify = MagicMock()
        mock_spotify.current_user_playlists.return_value = {'invalid': 'response'}

        with patch('backend.spotify.src.api.spotify.spotipy.Spotify', return_value=mock_spotify):
            result = _get_playlists(self.access_token)

            self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()