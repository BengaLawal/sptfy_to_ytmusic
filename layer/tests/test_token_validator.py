import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from layer.python.shared_utils.token_validator import is_token_valid


@pytest.fixture
def mock_db_service():
    """Create a mock database service."""
    return Mock()


@pytest.fixture
def mock_refresh_callback():
    """Create a mock refresh callback function."""
    return Mock()


@pytest.fixture
def valid_tokens():
    """Create sample valid tokens."""
    current_time = int(datetime.now().timestamp())
    return {
        'spotify_access_token': 'valid_access_token',
        'spotify_expires_at': current_time + 3600,  # expires in 1 hour
        'spotify_refresh_token': 'valid_refresh_token'
    }


@pytest.fixture
def expired_tokens():
    """Create sample expired tokens."""
    current_time = int(datetime.now().timestamp())
    return {
        'spotify_access_token': 'expired_access_token',
        'spotify_expires_at': current_time - 3600,  # expired 1 hour ago
        'spotify_refresh_token': 'valid_refresh_token'
    }


def test_valid_token(mock_db_service, mock_refresh_callback, valid_tokens):
    """Test when token is valid and not expired."""
    mock_db_service.get_tokens.return_value = valid_tokens

    result = is_token_valid(
        mock_db_service,
        'test_user',
        'spotify',
        mock_refresh_callback
    )

    assert result == 'valid_access_token'
    mock_refresh_callback.assert_not_called()


def test_expired_token_successful_refresh(mock_db_service, mock_refresh_callback, expired_tokens):
    """Test when token is expired and successfully refreshed."""
    mock_db_service.get_tokens.return_value = expired_tokens
    mock_refresh_callback.return_value = 'new_access_token'

    result = is_token_valid(
        mock_db_service,
        'test_user',
        'spotify',
        mock_refresh_callback
    )

    assert result == 'new_access_token'
    mock_refresh_callback.assert_called_once_with('test_user', 'valid_refresh_token')


def test_expired_token_refresh_fails(mock_db_service, mock_refresh_callback, expired_tokens):
    """Test when token is expired and refresh fails."""
    mock_db_service.get_tokens.return_value = expired_tokens
    mock_refresh_callback.return_value = None

    result = is_token_valid(
        mock_db_service,
        'test_user',
        'spotify',
        mock_refresh_callback
    )

    assert result is None
    mock_refresh_callback.assert_called_once_with('test_user', 'valid_refresh_token')


def test_no_tokens_found(mock_db_service, mock_refresh_callback):
    """Test when no tokens are found for user."""
    mock_db_service.get_tokens.return_value = None

    result = is_token_valid(
        mock_db_service,
        'test_user',
        'spotify',
        mock_refresh_callback
    )

    assert result is None
    mock_refresh_callback.assert_not_called()


def test_invalid_expires_at_format(mock_db_service, mock_refresh_callback):
    """Test handling of invalid expires_at format."""
    tokens = {
        'spotify_access_token': 'access_token',
        'spotify_expires_at': 'invalid_timestamp',
        'spotify_refresh_token': 'refresh_token'
    }
    mock_db_service.get_tokens.return_value = tokens

    result = is_token_valid(
        mock_db_service,
        'test_user',
        'spotify',
        mock_refresh_callback
    )

    assert result is None


def test_missing_expires_at(mock_db_service, mock_refresh_callback):
    """Test handling of missing expires_at field."""
    tokens = {
        'spotify_access_token': 'access_token',
        'spotify_refresh_token': 'refresh_token'
    }
    mock_db_service.get_tokens.return_value = tokens
    mock_refresh_callback.return_value = 'new_access_token'

    result = is_token_valid(
        mock_db_service,
        'test_user',
        'spotify',
        mock_refresh_callback
    )

    assert result == 'new_access_token'
    mock_refresh_callback.assert_called_once_with('test_user', 'refresh_token')


def test_db_service_raises_exception(mock_db_service, mock_refresh_callback):
    """Test handling of database service exception."""
    mock_db_service.get_tokens.side_effect = Exception("Database error")

    result = is_token_valid(
        mock_db_service,
        'test_user',
        'spotify',
        mock_refresh_callback
    )

    assert result is None
    mock_refresh_callback.assert_not_called()