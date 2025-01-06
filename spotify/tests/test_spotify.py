import os
import unittest
import boto3
import json
import spotipy
from moto import mock_aws
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, ANY, call
from botocore.exceptions import ClientError
from spotify.src.api.spotify import _get_secret, _store_spotify_token, _get_spotify_tokens, _is_token_valid, \
    _get_spotify_service, SCOPE, SPOTIPY_REDIRECT_URI, _refresh_spotify_token, _exchange_code_for_token, _get_playlists


def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"

class TestSpotifyHelpers(unittest.TestCase):
    """Test class for Spotify helper functions."""

    def setUp(self):
        aws_credentials()
        self.user_id = "test_user_123"
        self.current_time = int(datetime.now(timezone.utc).timestamp())
        self.token_info = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_in': 3600,
            'token_type': 'Bearer',
            'expires_at': int(datetime.now(timezone.utc).timestamp()) + 3600
        }
        self.region_name = "eu-west-1"
        self.secret_name = "Spotify"
        self.logger = MagicMock()

    def tearDown(self):
        # Clean up environment variables
        os.environ.pop("AWS_ACCESS_KEY_ID", None)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
        os.environ.pop("AWS_SECURITY_TOKEN", None)
        os.environ.pop("AWS_SESSION_TOKEN", None)
        os.environ.pop("AWS_DEFAULT_REGION", None)

    @mock_aws
    def test_get_secret_success(self):
        """Test successful retrieval of a secret from AWS Secrets Manager."""
        # Mock Secrets Manager
        client = boto3.client('secretsmanager', region_name=self.region_name)

        # Create a mock secret
        mock_secret_value = {
            "ClientID": "example-client-id",
            "ClientSecret": "example-client-secret"
        }
        client.create_secret(
            Name=self.secret_name,
            SecretString=json.dumps(mock_secret_value)
        )

        with patch('spotify.src.api.spotify.logger', self.logger):
            with patch('spotify.src.api.spotify.region_name', self.region_name):
                with patch('spotify.src.api.spotify.secret_name', self.secret_name):
                    secret = _get_secret()

        # Assertions
        self.assertEqual(secret, mock_secret_value)
        self.logger.error.assert_not_called()

    @mock_aws
    def test_get_secret_failure(self):
        """Test error handling when secret retrieval fails."""
        # Mock Secrets Manager
        client = boto3.client('secretsmanager', region_name=self.region_name)

        # Test the error case (secret doesn't exist)
        with patch('spotify.src.api.spotify.logger', self.logger):
            with patch('spotify.src.api.spotify.region_name', self.region_name):
                with patch('spotify.src.api.spotify.secret_name', self.secret_name):
                    with self.assertRaises(ClientError):
                        _get_secret()

        # Check that logging was invoked
        self.logger.error.assert_called_once()

    def _create_token_data(self, expires_in_seconds=3600):
        """Helper function to create token data."""
        return {
            'spotify_access_token': self.token_info['access_token'],
            'spotify_refresh_token': self.token_info['refresh_token'],
            'spotify_expires_at': self.current_time + expires_in_seconds,
            'spotify_token_type': self.token_info['token_type']
        }

    def _mock_dynamodb_table(self):
        """Helper function to create a mock DynamoDB table."""
        dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
        table = dynamodb.create_table(
            TableName='TestUsers',
            KeySchema=[
                {'AttributeName': 'userid', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userid', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )
        table.wait_until_exists()
        return table

    @mock_aws()
    def test_store_spotify_token_success(self):
        users_table = self._mock_dynamodb_table()
        users_table.put_item(Item={'userid': self.user_id})

        with patch('spotify.src.api.spotify.users_table', users_table), \
                patch('spotify.src.api.spotify.logger', self.logger):

            result = _store_spotify_token(self.user_id, self.token_info)

            # Assert
            self.assertTrue(result)
            response = users_table.get_item(Key={'userid': self.user_id})
            item = response['Item']
            self.assertEqual(item['spotify_access_token'], self.token_info['access_token'])
            self.assertEqual(item['spotify_refresh_token'], self.token_info['refresh_token'])
            self.assertEqual(item['spotify_expires_in'], self.token_info['expires_in'])
            self.assertEqual(item['spotify_token_type'], self.token_info['token_type'])
            self.assertEqual(item['spotify_expires_at'], self.token_info['expires_at'])

            # Verify logging
            self.logger.info.assert_called_once_with(f"Stored tokens for user {self.user_id}")
            self.logger.error.assert_not_called()

    @mock_aws
    def test_store_spotify_token_missing_user(self):
        """Test storing tokens for non-existent user."""
        table = self._mock_dynamodb_table()

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute and Assert
            with self.assertRaises(ClientError):
                _store_spotify_token("", self.token_info)

            self.logger.error.assert_called_once()

    @mock_aws
    def test_store_spotify_token_invalid_token_info(self):
        """Test storing invalid token information."""
        table = self._mock_dynamodb_table()
        table.put_item(Item={'userid': self.user_id})

        invalid_token_info = {
            'access_token': 'test_access_token'
            # Missing required fields
        }

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute and Assert
            with self.assertRaises(KeyError):
                _store_spotify_token(self.user_id, invalid_token_info)

            self.logger.error.assert_called_once()

    @mock_aws
    def test_store_spotify_token_empty_user_id(self):
        """Test storing tokens with empty user ID."""
        table = self._mock_dynamodb_table()

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute and Assert
            with self.assertRaises(Exception):
                _store_spotify_token("", self.token_info)

            self.logger.error.assert_called_once()

    @mock_aws
    def test_store_spotify_token_update_existing(self):
        """Test updating tokens for existing user."""
        table = self._mock_dynamodb_table()

        # Create initial token data
        initial_token_info = self.token_info.copy()
        initial_token_info['access_token'] = 'initial_access_token'

        # Store initial data
        table.put_item(Item={
            'userid': self.user_id,
            'spotify_access_token': initial_token_info['access_token']
        })

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute update
            result = _store_spotify_token(self.user_id, self.token_info)

            # Assert
            self.assertTrue(result)

            # Verify updated data
            response = table.get_item(Key={'userid': self.user_id})
            stored_data = response['Item']

            self.assertEqual(stored_data['spotify_access_token'], self.token_info['access_token'])
            self.assertNotEqual(stored_data['spotify_access_token'], initial_token_info['access_token'])

    @mock_aws()
    def test_store_spotify_token_timestamp_validation(self):
        """Test that the timestamp is properly set."""
        table = self._mock_dynamodb_table()
        table.put_item(Item={'userid': self.user_id})

        current_time = int(datetime.now(timezone.utc).timestamp())

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger):
            result = _store_spotify_token(self.user_id, self.token_info)

            # Assert
            self.assertTrue(result)

            response = table.get_item(Key={'userid': self.user_id})
            stored_data = response['Item']

            stored_timestamp = stored_data['spotify_token_updated']
            self.assertGreaterEqual(stored_timestamp, current_time)
            self.assertLess(stored_timestamp - current_time, 2)  # Should be within 2 seconds

    @mock_aws
    def test_get_spotify_tokens_success(self):
        """Test successful retrieval of Spotify tokens."""
        # Setup
        table = self._mock_dynamodb_table()
        self.token_data = {
            'spotify_access_token': 'test_access_token',
            'spotify_refresh_token': 'test_refresh_token',
            'spotify_expires_at': int(datetime.now(timezone.utc).timestamp()) + 3600
        }
        table.put_item(Item={
            'userid': self.user_id,
            **self.token_data
        })

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _get_spotify_tokens(self.user_id)

            # Assert
            self.assertIsNotNone(result)
            self.assertEqual(result['spotify_access_token'], self.token_data['spotify_access_token'])
            self.assertEqual(result['spotify_refresh_token'], self.token_data['spotify_refresh_token'])
            self.assertEqual(result['spotify_expires_at'], self.token_data['spotify_expires_at'])
            self.logger.error.assert_not_called()

    @mock_aws
    def test_get_spotify_tokens_missing_tokens(self):
        """Test retrieval for user without Spotify tokens."""
        table = self._mock_dynamodb_table()
        table.put_item(Item={
            'userid': self.user_id,
            'other_data': 'some_value'
        })

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _get_spotify_tokens(self.user_id)

            # Assert
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 0)  # Should return empty item
            self.logger.error.assert_not_called()

    @mock_aws
    def test_is_token_valid_success(self):
        """Test successful token validation."""
        # Setup
        table = self._mock_dynamodb_table()
        token_data = self._create_token_data()
        table.put_item(Item={'userid': self.user_id, **token_data})

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _is_token_valid(self.user_id)

            # Assert
            self.assertEqual(result, self.token_info['access_token'])
            self.logger.info.assert_any_call(f"Checking token validity for user {self.user_id}")
            self.logger.info.assert_any_call(f"Valid token found for user {self.user_id}")
            self.logger.error.assert_not_called()

    @mock_aws
    def test_is_token_valid_expired_with_refresh(self):
        """Test expired token with refresh token available."""
        # Setup
        table = self._mock_dynamodb_table()
        token_data = self._create_token_data(expires_in_seconds=-3600)  # expired token
        table.put_item(Item={'userid': self.user_id, **token_data})

        refreshed_token = "new_access_token"

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger), \
                patch('spotify.src.api.spotify._refresh_spotify_token') as mock_refresh:
            mock_refresh.return_value = refreshed_token

            # Execute
            result = _is_token_valid(self.user_id)

            # Assert
            self.assertEqual(result, refreshed_token)
            self.logger.info.assert_any_call(f"Token expired for user {self.user_id}")
            self.logger.info.assert_any_call(f"Attempting to refresh token for user {self.user_id}")
            mock_refresh.assert_called_once_with(
                self.user_id,
                token_data['spotify_refresh_token']
            )

    @mock_aws
    def test_is_token_valid_no_tokens(self):
        """Test when no tokens are found."""
        # Setup
        table = self._mock_dynamodb_table()

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _is_token_valid(self.user_id)

            # Assert
            self.assertIsNone(result)
            self.logger.info.assert_called_with(f"No tokens found for user {self.user_id}")

    @mock_aws
    def test_is_token_valid_expired_no_refresh(self):
        """Test expired token without refresh token."""
        # Setup
        table = self._mock_dynamodb_table()
        token_data = {
            'userid': self.user_id,
            'spotify_access_token': self.token_info['access_token'],
            'spotify_expires_at': self.current_time - 3600  # expired
        }
        table.put_item(Item=token_data)

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _is_token_valid(self.user_id)

            # Assert
            self.assertIsNone(result)
            self.logger.info.assert_any_call(f"Token expired for user {self.user_id}")
            self.logger.info.assert_any_call(f"No refresh token found for user {self.user_id}")

    @mock_aws
    def test_refresh_spotify_token_success(self):
        """Test successful token refresh and update."""
        # Setup
        table = self._mock_dynamodb_table()
        current_time = int(datetime.now(timezone.utc).timestamp())
        new_token_info = {
            'access_token': 'new_access_token',
            'expires_at': current_time + 3600,
            'refresh_token': 'new_refresh_token'
        }

        mock_spotify = MagicMock()
        mock_spotify.auth_manager.refresh_access_token.return_value = new_token_info

        with patch('spotify.src.api.spotify.users_table', table), \
                patch('spotify.src.api.spotify._get_spotify_service', return_value=mock_spotify), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _refresh_spotify_token(self.user_id, 'old_refresh_token')

            # Assert
            self.assertEqual(result, new_token_info['access_token'])

            # Verify DynamoDB update
            response = table.get_item(Key={'userid': self.user_id})
            self.assertIn('Item', response)
            self.assertEqual(response['Item']['spotify_access_token'], new_token_info['access_token'])
            self.assertEqual(response['Item']['spotify_refresh_token'], new_token_info['refresh_token'])
            self.assertEqual(response['Item']['spotify_expires_at'], new_token_info['expires_at'])

            # Verify logging
            self.logger.info.assert_any_call(f"new token info: {new_token_info}")
            self.logger.info.assert_any_call(f"Refreshed token for user {self.user_id}")


def _sample_playlist_data():
    """Helper method to create sample playlist data."""
    return {
        'collaborative': False,
        'description': "",
        'external_urls': {
            'spotify': 'https://open.spotify.com/playlist/2Nyw64tkZwej3qSA6B3W8F'
        },
        'href': "https://api.spotify.com/v1/playlists/2Nyw64tkZwej3qSA6B3W8F",
        'id': "2Nyw64tkZwej3qSA6B3W8F",
        'images': [{
            'url': 'https://example.com/image.jpg',
            'height': 640,
            'width': 640
        }],
        'name': "If this world were mine",
        'owner': {
            'display_name': 'G_Benga',
            'external_urls': {
                'spotify': 'https://open.spotify.com/user/vw3vdbtnoihkfle5w3f8zhe5n'
            },
            'href': 'https://api.spotify.com/v1/users/vw3vdbtnoihkfle5w3f8zhe5n',
            'id': 'XXXXXXXXXXXXXXXXXXXXXXXXX',
            'type': 'user'
        },
        'primary_color': None,
        'public': True,
        'snapshot_id': "AAAArBXSEQs9dfyKNlGGX2UQ5FiS6D6k",
        'tracks': {
            'href': 'https://api.spotify.com/v1/playlists/2Nyw64tkZwej3qSA6B3W8F/tracks',
            'total': 25
        },
        'type': "playlist",
        'uri': "spotify:playlist:2Nyw64tkZwej3qSA6B3W8F"

    }


class TestSpotifyMain(unittest.TestCase):
    """Test class for main Spotify functionality."""

    def setUp(self):
        aws_credentials()
        self.access_token = "test_access_token"
        self.user_id = "test_user_123"
        self.logger = MagicMock()
        self.spotify_client = MagicMock()

    def tearDown(self):
        # Clean up environment variables
        os.environ.pop("AWS_ACCESS_KEY_ID", None)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
        os.environ.pop("AWS_SECURITY_TOKEN", None)
        os.environ.pop("AWS_SESSION_TOKEN", None)
        os.environ.pop("AWS_DEFAULT_REGION", None)

    @mock_aws
    def test_get_spotify_service_success(self):
        """Test successful creation of Spotify service instance."""
        # Setup
        mock_secrets = {
            "SPOTIPY_CLIENT_ID": "test_client_id",
            "SPOTIPY_CLIENT_SECRET": "test_client_secret"
        }
        mock_spotify = MagicMock()

        with patch('spotify.src.api.spotify._get_secret', return_value=mock_secrets), \
                patch('spotify.src.api.spotify.spotipy.Spotify', return_value=mock_spotify), \
                patch('spotify.src.api.spotify.SpotifyOAuth') as mock_oauth:
            # Execute
            result = _get_spotify_service()

            # Assert
            self.assertEqual(result, mock_spotify)
            mock_oauth.assert_called_once_with(
                client_id=mock_secrets["SPOTIPY_CLIENT_ID"],
                client_secret=mock_secrets["SPOTIPY_CLIENT_SECRET"],
                redirect_uri=SPOTIPY_REDIRECT_URI,
                scope=SCOPE,
                open_browser=True,
                show_dialog=True,
                cache_handler=ANY
            )

    @mock_aws
    def test_get_spotify_service_failure(self):
        """Test failure in creation of Spotify service instance."""
        # Setup
        mock_secrets = {
            "SPOTIPY_CLIENT_ID": "test_client_id",
            "SPOTIPY_CLIENT_SECRET": "test_client_secret"
        }
        mock_error = spotipy.SpotifyOauthError("Failed to create Spotify OAuth")

        with patch('spotify.src.api.spotify._get_secret', return_value=mock_secrets), \
                patch('spotify.src.api.spotify.SpotifyOAuth', side_effect=mock_error), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute and Assert
            with self.assertRaises(spotipy.SpotifyOauthError):
                _get_spotify_service()

            # Verify error was logged
            self.logger.error.assert_called_once_with(
                "Error creating Spotify service: Failed to create Spotify OAuth"
            )

    @mock_aws
    def test_get_spotify_service_missing_secrets(self):
        """Test handling of missing secret values."""
        # Setup
        mock_secrets = {
            # Missing required secrets
        }

        with patch('spotify.src.api.spotify._get_secret', return_value=mock_secrets), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute and Assert
            with self.assertRaises(KeyError):
                _get_spotify_service()

            self.logger.error.assert_called()

    @mock_aws
    def test_exchange_code_for_token_success(self):
        """Test successful code exchange for token."""
        # Setup
        mock_code = "test_auth_code"
        expected_token_info = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_at': int(datetime.now(timezone.utc).timestamp()) + 3600,
            'scope': 'user-library-read',
            'token_type': 'Bearer'
        }

        mock_auth_manager = MagicMock()
        mock_auth_manager.get_cached_token.return_value = expected_token_info

        mock_spotify = MagicMock()
        mock_spotify.auth_manager = mock_auth_manager

        with patch('spotify.src.api.spotify._get_spotify_service', return_value=mock_spotify), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _exchange_code_for_token(mock_code)

            # Assert
            self.assertEqual(result, expected_token_info)
            mock_auth_manager.get_access_token.assert_called_once_with(
                code=mock_code,
                as_dict=False,
                check_cache=True
            )
            mock_auth_manager.get_cached_token.assert_called_once()
            self.logger.info.assert_called_once_with(expected_token_info)

    @mock_aws
    def test_exchange_code_for_token_oauth_error(self):
        """Test handling of OAuth error during code exchange."""
        # Setup
        mock_code = "invalid_code"
        mock_auth_manager = MagicMock()
        mock_auth_manager.get_access_token.side_effect = spotipy.SpotifyOauthError("Invalid code")

        mock_spotify = MagicMock()
        mock_spotify.auth_manager = mock_auth_manager

        with patch('spotify.src.api.spotify._get_spotify_service', return_value=mock_spotify), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _exchange_code_for_token(mock_code)

            # Assert
            self.assertIsNone(result)
            self.logger.error.assert_called_once_with(
                "OAuth error during token exchange: Invalid code"
            )

    def test_get_playlists_single_page(self):
        """Test successful retrieval of playlists fitting in single page."""
        # Setup
        mock_response = {
            'items': [_sample_playlist_data()],
            'next': None
        }

        mock_spotify = MagicMock()
        mock_spotify.current_user_playlists.return_value = mock_response

        with patch('spotify.src.api.spotify.spotipy.Spotify', return_value=mock_spotify), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _get_playlists(self.access_token)

            # Assert
            self.assertIsNotNone(result)
            self.assertEqual(len(result['items']), 1)
            self.assertEqual(result['total'], 1)

            # Verify playlist structure
            playlist = result['items'][0]
            self.assertEqual(playlist['id'], "2Nyw64tkZwej3qSA6B3W8F")
            self.assertEqual(playlist['name'], "If this world were mine")
            self.assertEqual(playlist['tracks']['total'], 25)
            self.assertEqual(playlist['owner']['display_name'], "G_Benga")

            # Verify API call
            mock_spotify.current_user_playlists.assert_called_once_with(
                limit=50, offset=0
            )

    def test_get_playlists_multiple_pages(self):
        """Test retrieval of playlists across multiple pages."""
        # Setup
        first_page = {
            'items': [_sample_playlist_data()] * 50,  # 50 copies of sample playlist
            'next': 'next_page_url'
        }

        second_page = {
            'items': [
                {**_sample_playlist_data(), 'id': f"modified_id_{i}"}
                for i in range(10)
            ],
            'next': None
        }

        mock_spotify = MagicMock()
        mock_spotify.current_user_playlists.side_effect = [first_page, second_page]

        with patch('spotify.src.api.spotify.spotipy.Spotify', return_value=mock_spotify), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _get_playlists(self.access_token)

            # Assert
            self.assertIsNotNone(result)
            self.assertEqual(len(result['items']), 60)
            self.assertEqual(result['total'], 60)

            # Verify pagination
            calls = [
                call(limit=50, offset=0),
                call(limit=50, offset=50)
            ]
            mock_spotify.current_user_playlists.assert_has_calls(calls)

    def test_get_playlists_empty_response(self):
        """Test handling of empty playlist response."""
        # Setup
        mock_response = {
            'items': [],
            'next': None
        }

        mock_spotify = MagicMock()
        mock_spotify.current_user_playlists.return_value = mock_response

        with patch('spotify.src.api.spotify.spotipy.Spotify', return_value=mock_spotify), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _get_playlists(self.access_token)

            # Assert
            self.assertIsNotNone(result)
            self.assertEqual(len(result['items']), 0)
            self.assertEqual(result['total'], 0)

    def test_get_playlists_invalid_response(self):
        """Test handling of invalid API response."""
        # Setup
        mock_spotify = MagicMock()
        mock_spotify.current_user_playlists.return_value = {'invalid': 'response'}

        with patch('spotify.src.api.spotify.spotipy.Spotify', return_value=mock_spotify), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _get_playlists(self.access_token)

            # Assert
            self.assertIsNone(result)
            self.logger.error.assert_called_once_with(
                "Invalid response format from Spotify API"
            )

    def test_get_playlists_verify_playlist_structure(self):
        """Test that each playlist has the required fields."""
        # Setup
        mock_response = {
            'items': [_sample_playlist_data()],
            'next': None
        }

        mock_spotify = MagicMock()
        mock_spotify.current_user_playlists.return_value = mock_response

        with patch('spotify.src.api.spotify.spotipy.Spotify', return_value=mock_spotify), \
                patch('spotify.src.api.spotify.logger', self.logger):
            # Execute
            result = _get_playlists(self.access_token)

            # Assert
            self.assertIsNotNone(result)
            playlist = result['items'][0]

            # Verify required fields
            required_fields = [
                'id', 'name', 'owner', 'tracks', 'uri',
                'external_urls', 'collaborative', 'public'
            ]
            for field in required_fields:
                self.assertIn(field, playlist)

            # Verify nested structures
            self.assertIn('total', playlist['tracks'])
            self.assertIn('display_name', playlist['owner'])
            self.assertIn('spotify', playlist['external_urls'])

if __name__ == '__main__':
    unittest.main()
