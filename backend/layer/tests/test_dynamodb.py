import pytest
import boto3
import os
from moto import mock_aws
from datetime import datetime, timezone
from shared_utils.dynamodb import DynamoDBService  # Assuming the class is in dynamodb_service.py


@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture(scope='function')
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb')

        # Create the mock table
        table = dynamodb.create_table(
            TableName='test_tokens',
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

        # Create a test user
        table.put_item(Item={
            'userid': 'test_user_1',
            'spotify_access_token': 'old_access_token',
            'spotify_refresh_token': 'old_refresh_token',
            'spotify_expires_at': int(datetime.now(timezone.utc).timestamp()) + 3600,
            'spotify_token_type': 'Bearer'
        })

        yield table


@pytest.fixture(scope='function')
def dynamodb_service(dynamodb_table):
    """Create a DynamoDBService instance with the mock table."""
    return DynamoDBService('test_tokens')


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