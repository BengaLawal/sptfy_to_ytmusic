import pytest
import boto3
import json
from moto import mock_aws
import os
from botocore.exceptions import ClientError
from shared_utils.secrets_manager import get_secret  # Assuming the function is in secrets_manager.py


@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@pytest.fixture(scope='function')
def secretsmanager_client(aws_credentials):
    """Create mock Secrets Manager client."""
    with mock_aws():
        region = 'eu-west-1'
        client = boto3.client('secretsmanager', region_name=region)
        yield client


@pytest.fixture(scope='function')
def sample_secret(secretsmanager_client):
    """Create a sample secret in mock Secrets Manager."""
    secret_name = 'test/secret'
    secret_value = {
        'SPOTIPY_CLIENT_ID': 'ID',
        'SPOTIPY_CLIENT_SECRET': 'SECRET',
    }
    secretsmanager_client.create_secret(
        Name=secret_name,
        SecretString=json.dumps(secret_value)
    )
    return secret_name, secret_value


def test_get_secret_success(sample_secret):
    """Test successful secret retrieval."""
    secret_name, expected_value = sample_secret
    result = get_secret('eu-west-1', secret_name)

    assert result == expected_value
    assert 'SPOTIPY_CLIENT_SECRET' in result
    assert result['SPOTIPY_CLIENT_SECRET'] == 'SECRET'
    assert 'SPOTIPY_CLIENT_ID' in result
    assert result['SPOTIPY_CLIENT_ID'] == 'ID'


def test_get_secret_nonexistent(secretsmanager_client):
    """Test retrieving a non-existent secret."""
    with pytest.raises(ClientError) as exc_info:
        get_secret('us-east-1', 'nonexistent')

    assert 'ResourceNotFoundException' in str(exc_info.value)