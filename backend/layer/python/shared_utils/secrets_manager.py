import boto3
import json
import logging
from botocore.exceptions import ClientError
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_secret(region_name: str, secret_name: str) -> Dict[str, Any]:
    """Retrieve secret from AWS Secrets Manager.

    Args:
        region_name (str): AWS region name where secret is stored
        secret_name (str): Name of the secret to retrieve

    Returns:
        Dict[str, Any]: Dictionary containing the secret key/value pairs

    Raises:
        ClientError: If there is an error retrieving the secret
    """
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        return json.loads(get_secret_value_response['SecretString'])
    except ClientError as e:
        logger.error(f"Error retrieving secret: {e}")
        raise e