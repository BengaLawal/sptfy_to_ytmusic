import os
import boto3
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from moto import mock_aws
from ytmusicapi.auth.oauth import OAuthCredentials

from backend.ytmusic.src.api.ytmusic import (
    _get_oauth, _get_oauth_data, _refresh_ytmusic_token, _create_ytmusic_playlist, _search_and_add_tracks,
)


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


class TestYTMusicHelpers(unittest.TestCase):
    """Test class for YTMusic helper functions."""

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
            'YTMUSIC_CLIENT_ID': 'test_client_id',
            'YTMUSIC_CLIENT_SECRET': 'test_client_secret'
        }
        self.mock_code = {
            'device_code': 'test_device_code',
            'user_code': 'test_user_code',
            'verification_url': 'https://example.com/verify',
            'interval': 5,
            'expires_in': 1800
        }
        self.logger = MagicMock()

    def tearDown(self):
        for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SECURITY_TOKEN",
                    "AWS_SESSION_TOKEN", "AWS_DEFAULT_REGION"]:
            os.environ.pop(key, None)

    @mock_aws
    def test_get_oauth_success(self):
        """Test successful creation of OAuth credentials."""
        with patch('backend.ytmusic.src.api.ytmusic.get_secret', return_value=self.mock_secrets):
            oauth = _get_oauth()

            self.assertIsInstance(oauth, OAuthCredentials)
            self.assertEqual(oauth.client_id, self.mock_secrets['YTMUSIC_CLIENT_ID'])
            self.assertEqual(oauth.client_secret, self.mock_secrets['YTMUSIC_CLIENT_SECRET'])

    @mock_aws
    def test_get_oauth_data_success(self):
        """Test successful retrieval of OAuth data."""
        mock_oauth = MagicMock()
        mock_oauth.get_code.return_value = self.mock_code

        with patch('backend.ytmusic.src.api.ytmusic._get_oauth', return_value=mock_oauth):
            result = _get_oauth_data()

            self.assertEqual(result['verification_url'],
                             f"{self.mock_code['verification_url']}?user_code={self.mock_code['user_code']}")
            self.assertEqual(result['device_code'], self.mock_code['device_code'])
            self.assertEqual(result['interval'], self.mock_code['interval'])
            self.assertEqual(result['expires_in'], self.mock_code['expires_in'])


    @mock_aws
    def test_refresh_ytmusic_token_success(self):
        """Test successful token refresh."""
        table = _mock_dynamodb_table()
        table.put_item(Item={'userid': self.user_id})

        mock_oauth = MagicMock()
        mock_oauth.refresh_token.return_value = self.token_info

        with patch('backend.ytmusic.src.api.ytmusic._get_oauth', return_value=mock_oauth), \
                patch('backend.ytmusic.src.api.ytmusic.db_service.update_token', return_value=True):
            result = _refresh_ytmusic_token(self.user_id, self.refresh_token)

            self.assertEqual(result, self.token_info['access_token'])
            mock_oauth.refresh_token.assert_called_once_with(self.refresh_token)

    @mock_aws
    def test_refresh_ytmusic_token_update_failure(self):
        """Test token refresh with database update failure."""
        mock_oauth = MagicMock()
        mock_oauth.refresh_token.return_value = self.token_info

        with patch('backend.ytmusic.src.api.ytmusic._get_oauth', return_value=mock_oauth), \
                patch('backend.ytmusic.src.api.ytmusic.db_service.update_token', return_value=False):
            result = _refresh_ytmusic_token(self.user_id, self.refresh_token)

            self.assertIsNone(result)

    @mock_aws
    def test_create_ytmusic_playlist_success(self):
        """Test successful creation of a YouTube Music playlist."""
        mock_ytmusic_client = MagicMock()
        mock_ytmusic_client.create_playlist.return_value = "test_playlist_id"
        playlist_name = "Test Playlist"
        description = "This is a test playlist."

        playlist_id = _create_ytmusic_playlist(mock_ytmusic_client, playlist_name, description)

        self.assertEqual(playlist_id, "test_playlist_id")
        mock_ytmusic_client.create_playlist.assert_called_once_with(
            title=playlist_name,
            description=description,
            privacy_status='PRIVATE'
        )

    @mock_aws
    def test_create_ytmusic_playlist_failure(self):
        """Test failure in creating a YouTube Music playlist."""
        mock_ytmusic_client = MagicMock()
        mock_ytmusic_client.create_playlist.side_effect = Exception("Failed to create playlist")

        playlist_name = "Test Playlist"

        with self.assertRaises(Exception) as context:
            _create_ytmusic_playlist(mock_ytmusic_client, playlist_name)

        self.assertEqual(str(context.exception), "Failed to create playlist")
        mock_ytmusic_client.create_playlist.assert_called_once_with(
            title=playlist_name,
            description="",
            privacy_status='PRIVATE'
        )

    @mock_aws
    def test_search_and_add_tracks_success(self):
        """Test successful search and addition of tracks to a playlist."""
        mock_ytmusic_client = MagicMock()
        mock_ytmusic_client.search.return_value = [{'videoId': 'test_video_id'}]
        mock_ytmusic_client.add_playlist_items.return_value = None

        playlist_id = "test_playlist_id"
        tracks = [{'name': 'Test Track', 'artists': ['Test Artist']}]

        results = _search_and_add_tracks(mock_ytmusic_client, playlist_id, tracks)

        self.assertEqual(results['successful'], 1)
        self.assertEqual(results['failed'], 0)
        self.assertEqual(results['not_found'], 0)
        mock_ytmusic_client.search.assert_called_once_with("Test Track Test Artist", filter='songs', limit=1)
        mock_ytmusic_client.add_playlist_items.assert_called_once_with(playlist_id, ['test_video_id'])

    @mock_aws
    def test_search_and_add_tracks_not_found(self):
        """Test track not found scenario during search and addition."""
        mock_ytmusic_client = MagicMock()
        mock_ytmusic_client.search.return_value = []

        playlist_id = "test_playlist_id"
        tracks = [{'name': 'Nonexistent Track', 'artists': ['Nonexistent Artist']}]

        results = _search_and_add_tracks(mock_ytmusic_client, playlist_id, tracks)

        self.assertEqual(results['successful'], 0)
        self.assertEqual(results['failed'], 0)
        self.assertEqual(results['not_found'], 1)
        mock_ytmusic_client.search.assert_called_once_with("Nonexistent Track Nonexistent Artist", filter='songs',
                                                           limit=1)

    @mock_aws
    def test_search_and_add_tracks_failure(self):
        """Test failure in adding a track to a playlist."""
        mock_ytmusic_client = MagicMock()
        mock_ytmusic_client.search.return_value = [{'videoId': 'test_video_id'}]
        mock_ytmusic_client.add_playlist_items.side_effect = Exception("Failed to add track")

        playlist_id = "test_playlist_id"
        tracks = [{'name': 'Test Track', 'artists': ['Test Artist']}]

        results = _search_and_add_tracks(mock_ytmusic_client, playlist_id, tracks)

        self.assertEqual(results['successful'], 0)
        self.assertEqual(results['failed'], 1)
        self.assertEqual(results['not_found'], 0)
        mock_ytmusic_client.search.assert_called_once_with("Test Track Test Artist", filter='songs', limit=1)

if __name__ == '__main__':
    unittest.main()