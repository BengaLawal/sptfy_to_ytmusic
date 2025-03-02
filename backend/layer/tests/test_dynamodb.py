import pytest
import boto3
import os
import decimal
from moto import mock_aws
from datetime import datetime, timezone
from shared_utils.dynamodb import DynamoDBService


@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture(scope='function')
def dynamodb_tables(aws_credentials):
    """Create mock DynamoDB tables."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb')

        # Create users table
        users_table = dynamodb.create_table(
            TableName='test_users',
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

        # Create transfers table
        transfer_table = dynamodb.create_table(
            TableName='test_transfers',
            KeySchema=[
                {'AttributeName': 'transfer_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'transfer_id', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )

        # Create a test user
        users_table.put_item(Item={
            'userid': 'test_user_1',
            'spotify_access_token': 'old_access_token',
            'spotify_refresh_token': 'old_refresh_token',
            'spotify_expires_at': int(datetime.now(timezone.utc).timestamp()) + 3600,
            'spotify_token_type': 'Bearer'
        })
        yield users_table, transfer_table


@pytest.fixture(scope='function')
def dynamodb_service(dynamodb_tables):
    """Create a DynamoDBService instance with mock tables."""
    users_table, transfer_table = dynamodb_tables
    return DynamoDBService('test_users', 'test_transfers')


def test_get_tokens_success(dynamodb_service):
    """Test successful token retrieval."""
    tokens = dynamodb_service.get_tokens('test_user_1', 'spotify')

    assert tokens is not None
    assert 'spotify_access_token' in tokens
    assert tokens['spotify_access_token'] == 'old_access_token'
    assert 'spotify_refresh_token' in tokens
    assert tokens['spotify_refresh_token'] == 'old_refresh_token'


def test_get_tokens_nonexistent_user(dynamodb_service):
    """Test token retrieval for non-existent user."""
    tokens = dynamodb_service.get_tokens('nonexistent_user', 'spotify')
    assert tokens is None


def test_store_tokens_success(dynamodb_service):
    """Test successful token storage."""
    token_info = {
        'access_token': 'new_access_token',
        'refresh_token': 'new_refresh_token',
        'expires_in': 3600,
        'token_type': 'Bearer'
    }

    result = dynamodb_service.store_tokens('test_user_1', token_info, 'spotify')
    assert result is True

    # Verify the tokens were stored
    stored_tokens = dynamodb_service.get_tokens('test_user_1', 'spotify')
    assert stored_tokens['spotify_access_token'] == 'new_access_token'
    assert stored_tokens['spotify_refresh_token'] == 'new_refresh_token'


def test_store_tokens_nonexistent_user(dynamodb_service):
    """Test token storage for non-existent user."""
    token_info = {
        'access_token': 'new_access_token',
        'refresh_token': 'new_refresh_token',
        'expires_in': 3600,
        'token_type': 'Bearer'
    }

    with pytest.raises(ValueError, match="User nonexistent_user does not exist"):
        dynamodb_service.store_tokens('nonexistent_user', token_info, 'spotify')


def test_update_token_success(dynamodb_service):
    """Test successful token update."""
    token_info = {
        'access_token': 'updated_access_token',
        'expires_in': 3600
    }

    result = dynamodb_service.update_token('test_user_1', token_info, 'spotify')
    assert result is True

    # Verify the token was updated
    updated_tokens = dynamodb_service.get_tokens('test_user_1', 'spotify')
    assert updated_tokens['spotify_access_token'] == 'updated_access_token'


def test_update_token_with_refresh(dynamodb_service):
    """Test token update including refresh token."""
    token_info = {
        'access_token': 'updated_access_token',
        'refresh_token': 'updated_refresh_token',
        'expires_in': 3600
    }

    result = dynamodb_service.update_token('test_user_1', token_info, 'spotify')
    assert result is True

    # Verify both tokens were updated
    updated_tokens = dynamodb_service.get_tokens('test_user_1', 'spotify')
    assert updated_tokens['spotify_access_token'] == 'updated_access_token'
    assert updated_tokens['spotify_refresh_token'] == 'updated_refresh_token'


def test_update_transfer_details(dynamodb_service):
    """Test updating transfer details."""
    transfer_details = {
        'transfer_id': 'transfer_123',
        'user_id': 'test_user_1',
        'timestamp_started': int(datetime.now(timezone.utc).timestamp()),
        'status': 'in_progress',
        'total_playlists': 3,
        'total_tracks': 0,
        'completed_playlists': 0,
        'completed_tracks': 0,
        'failed_playlists': 0,
        'failed_tracks': 0,
        'playlists': [],
        'error_details': None
    }

    dynamodb_service.update_transfer_details('transfer_123', transfer_details)

    retrieved_details = dynamodb_service.get_transfer_details('transfer_123')

    assert retrieved_details['transfer_id'] == 'transfer_123'
    assert retrieved_details['user_id'] == 'test_user_1'
    assert retrieved_details['status'] == 'in_progress'
    assert retrieved_details['total_playlists'] == 3
    assert retrieved_details['playlists'] == []
    assert retrieved_details['error_details'] is None