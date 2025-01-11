import boto3
import logging
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DynamoDBService:
    """Service class for interacting with DynamoDB to manage user tokens."""

    def __init__(self, table_name: str) -> None:
        """Initialize DynamoDB service with table name.

        Args:
            table_name (str): Name of the DynamoDB table to use
        """
        self.table_name: str = table_name
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def get_tokens(self, user_id: str, service_prefix: str) -> Optional[Dict[str, Any]]:
        """Get tokens from DynamoDB for the specified service.

        Args:
            user_id (str): Unique identifier for the user
            service_prefix (str): Prefix identifying the service (e.g. 'spotify', 'github')

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing token information if found, None otherwise
        """
        try:
            projection_expression = f"{service_prefix}_access_token, {service_prefix}_expires_at, {service_prefix}_refresh_token"
            response = self.table.get_item(
                Key={'userid': user_id},
                ProjectionExpression=projection_expression
            )
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error accessing DynamoDB: {e.response['Error']['Message']}")
            return None

    def store_tokens(self, user_id: str, token_info: Dict[str, Any], service_prefix: str) -> bool:
        """Store service tokens in DynamoDB.

        Args:
            user_id (str): Unique identifier for the user
            token_info (Dict[str, Any]): Dictionary containing token information to store
            service_prefix (str): Prefix identifying the service (e.g. 'spotify', 'ytmusic')

        Returns:
            bool: True if tokens were stored successfully

        Raises:
            ValueError: If user does not exist
            Exception: If there is an error storing the tokens
        """
        try:
            response = self.table.get_item(Key={'userid': user_id})
            if 'Item' not in response:
                raise ValueError(f"User {user_id} does not exist")

            update_expression = f"""
                SET {service_prefix}_access_token = :access_token,
                    {service_prefix}_refresh_token = :refresh_token,
                    {service_prefix}_expires_in = :expires_in,
                    {service_prefix}_token_type = :token_type,
                    {service_prefix}_expires_at = :expires_at,
                    {service_prefix}_token_updated = :updated_at
            """

            self.table.update_item(
                Key={'userid': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues={
                    ':access_token': token_info['access_token'],
                    ':refresh_token': token_info['refresh_token'],
                    ':expires_in': token_info['expires_in'],
                    ':token_type': token_info['token_type'],
                    ':expires_at': token_info.get('expires_at', int(datetime.now(timezone.utc).timestamp() + token_info[
                        'expires_in'])),
                    ':updated_at': int(datetime.now(timezone.utc).timestamp())
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error storing tokens: {str(e)}")
            raise

    def update_token(self, user_id: str, token_info: Dict[str, Any], service_prefix: str) -> bool:
        """Update service access token in DynamoDB.

        Args:
            user_id (str): Unique identifier for the user
            token_info (Dict[str, Any]): Dictionary containing updated token information
            service_prefix (str): Prefix identifying the service (e.g. 'spotify', 'ytmusic')

        Returns:
            bool: True if token was updated successfully, False otherwise
        """
        try:
            update_expression = f"""
                SET {service_prefix}_access_token = :token,
                    {service_prefix}_expires_at = :exp,
                    {service_prefix}_token_updated = :updated
            """
            expression_values = {
                ':token': token_info['access_token'],
                ':exp': token_info.get('expires_at',
                                       int(datetime.now(timezone.utc).timestamp() + token_info['expires_in'])),
                ':updated': int(datetime.now().timestamp())
            }

            if 'refresh_token' in token_info:
                update_expression += f", {service_prefix}_refresh_token = :refresh"
                expression_values[':refresh'] = token_info['refresh_token']

            self.table.update_item(
                Key={'userid': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            return True
        except ClientError as e:
            logger.error(f"Error updating DynamoDB: {e.response['Error']['Message']}")
            return False