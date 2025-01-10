import json
from datetime import datetime, timezone
import boto3
import logging
from botocore.exceptions import ClientError
from ytmusicapi import YTMusic
from ytmusicapi.auth.oauth import OAuthCredentials
from ytmusicapi.setup import setup, setup_oauth


# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Environment Variables
# USERS_TABLE = os.environ['USERS_TABLE']
USERS_TABLE = "dev-UsersTable"
if not USERS_TABLE:
    raise ValueError("Environment variable 'USERS_TABLE' is not set.")

# DynamoDB setup
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USERS_TABLE)

# YtMusic configuration
YTMUSIC_REDIRECT_URI= "http://localhost:5173/ytmusic/callback"
region_name = "eu-west-1"
secret_name = "YtMusic"


def _get_secret(region, secret_id):
    """Retrieve secret from AWS Secrets Manager."""
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_id)
        return json.loads(get_secret_value_response['SecretString'])
    except ClientError as e:
        logger.error(f"Error retrieving secret: {e}")
        raise e


def _is_token_valid(userId):
    """Check and return valid YtMusic access token for the user.

    This function validates the YtMusic access token for a given user. It checks if:
    1. The user has stored tokens
    2. The access token exists and hasn't expired
    3. If expired, attempts to refresh using refresh token

    Args:
        userId (str): The unique identifier for the user

    Returns:
        str: Valid YtMusic access token if found and valid
        None: If no valid token exists or refresh fails

    Raises:
        Exception: If there is an error validating the token
    """
    try:
        tokens = _get_ytmusic_tokens(userId)
        if not tokens:
            logger.info(f"No tokens found for user {userId}")
            return None

        current_time = int(datetime.now().timestamp())
        logger.info(f"Checking token validity for user {userId}")

        # Check if access token exists and is still valid
        if 'ytmusic_access_token' in tokens and 'ytmusic_expires_at' in tokens:
            try:
                expires_at = int(tokens['ytmusic_expires_at'])
                if expires_at > current_time:
                    logger.info(f"Valid token found for user {userId}")
                    return tokens['ytmusic_access_token']
                logger.info(f"Token expired for user {userId}")
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting expires_at to int: {str(e)}")
                return None

        # If token expired and refresh token exists, try to refresh
        if 'ytmusic_refresh_token' in tokens:
            logger.info(f"Attempting to refresh token for user {userId}")
            return _refresh_ytmusic_token(userId, tokens['ytmusic_refresh_token'])

        logger.info(f"No refresh token found for user {userId}")
        return None

    except Exception as e:
        logger.error(f"Error validating token for user {userId}: {str(e)}")
        return None


def _refresh_ytmusic_token(userId, refresh_token):
    """Refresh YtMusic access token using the refresh token.

    This function attempts to refresh an expired YtMusic access token using the stored refresh token.
    It updates the user's token information in DynamoDB with the new access token and expiration time.

    Args:
        userId (str): The unique identifier for the user whose token to refresh
        refresh_token (str): The YtMusic refresh token to use for getting a new access token

    Returns:
        str: The new YtMusic access token if refresh was successful
        None: If there was an error refreshing the token or updating DynamoDB

    Raises:
        ClientError: If there is an error accessing DynamoDB
    """
    try:
        oauth = _get_oauth()
        new_token_info = oauth.refresh_token(refresh_token)
        logger.info(f"new token info: {new_token_info}")

        update_expression = 'SET ytmusic_access_token = :token, ytmusic_expires_at = :exp, ytmusic_token_updated = :updated'
        expression_values = {
            ':token': new_token_info['access_token'],
            ':exp': int(datetime.now(timezone.utc).timestamp() + new_token_info['expires_in']),
            ':updated': int(datetime.now().timestamp())
        }

        # If a new refresh token is provided, update it
        if 'refresh_token' in new_token_info:
            update_expression += ', ytmusic_refresh_token = :refresh'
            expression_values[':refresh'] = new_token_info['refresh_token']

        users_table.update_item(
            Key={'userid': userId},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        logger.info(f"Refreshed token for user {userId}")
        return new_token_info['access_token']
    except ClientError as e:
        logger.error(f"Error updating DynamoDB: {e.response['Error']['Message']}")
        return None


def _get_ytmusic_tokens(userId):
    """Retrieve YtMusic tokens from DynamoDB for the given user."""
    try:
        response = users_table.get_item(Key={'userid': userId},
                                        ProjectionExpression='ytmusic_access_token, ytmusic_expires_at, ytmusic_refresh_token')
        if 'Item' not in response:
            return None
        return response['Item']
    except ClientError as e:
        logger.error(f"Error accessing DynamoDB: {e.response['Error']['Message']}")
        return None


def _get_oauth():
    secrets = _get_secret(region_name, secret_name)
    oauth = OAuthCredentials(
        client_id=secrets['YTMUSIC_CLIENT_ID'],
        client_secret=secrets['YTMUSIC_CLIENT_SECRET'],
    )
    return oauth


def _get_oauth_data():
    """Get OAuth URL using YTMusic API directly"""
    oauth = _get_oauth()
    code = oauth.get_code()


    return {
        'verification_url': f"{code['verification_url']}?user_code={code['user_code']}",
        'device_code': code['device_code'],
        'interval': code.get('interval', 5),  # Polling interval in seconds
        'expires_in': code.get('expires_in', 1800)  # Token expiration in seconds
    }


def _store_ytmusic_token(userId, token_info):
    """Store YtMusic tokens in DynamoDB.

    This function stores or updates YtMusic authentication tokens for a given user in DynamoDB.
    It first checks if the user exists, then updates their record with the new token information.

    Args:
        userId (str): The unique identifier for the user
        token_info (dict): Dictionary containing YtMusic token information with the following keys:
            - access_token: The YtMusic access token
            - refresh_token: The YtMusic refresh token
            - expires_in: Token expiration time in seconds
            - token_type: Type of token (e.g. "Bearer")
            - expires_at: Timestamp when token expires

    Returns:
        bool: True if tokens were successfully stored

    Raises:
        ValueError: If the specified user does not exist in the database
        Exception: If there is an error storing the tokens
    """
    try:
        # First check if user exists
        response = users_table.get_item(
            Key={'userid': userId}
        )

        if 'Item' not in response:
            logger.error(f"User {userId} not found in database")
            raise ValueError(f"User {userId} does not exist")

        # Update user record with YtMusic tokens
        update_expression = """
            SET ytmusic_access_token = :access_token,
                ytmusic_refresh_token = :refresh_token,
                ytmusic_expires_in = :expires_in,
                ytmusic_token_type = :token_type,
                ytmusic_expires_at = :expires_at,
                ytmusic_token_updated = :updated_at
            """
        users_table.update_item(
            Key={'userid': userId},
            UpdateExpression=update_expression,
            ExpressionAttributeValues={
                ':access_token': token_info['access_token'],
                ':refresh_token': token_info['refresh_token'],
                ':expires_in': token_info['expires_in'],
                ':token_type': token_info['token_type'],
                ':expires_at': int(datetime.now(timezone.utc).timestamp() + token_info['expires_in']),
                ':updated_at': int(datetime.now(timezone.utc).timestamp())
            }
        )
        logger.info(f"Stored tokens for user {userId}")
        return True
    except Exception as e:
        logger.error(f"Error storing tokens: {str(e)}")
        raise

# ---------------------------------------------------------------------------------------

def handle_is_logged_in(event):
    """Handle the request to check if the user is logged in.

        This function validates whether a user is currently logged in by checking their
        access token validity.

        Args:
            event (dict): The API Gateway event object containing the request details
                         including pathParameters with userId

        Returns:
            dict: Response object containing:
                - statusCode (int): HTTP status code (200 for success, 400 for invalid request)
                - body (str): JSON string containing:
                    - message (str): Description of the response
                    - isLoggedIn (bool): True if user is logged in, False otherwise

        Raises:
            None: Exceptions are handled internally and returned as error responses
    """
    path_parameters = event.get('pathParameters', {})
    userId = path_parameters.get('userId')
    if not userId:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'userId is required in path parameters'
            })
        }

    access_token = _is_token_valid(userId)
    if access_token:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'User is logged in',
                'isLoggedIn': True,
            })
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'User is not logged in',
                'isLoggedIn': False,
            })
        }


def handle_login_ytmusic(event):
    """ Handle ytmusic login and redirect the user to the ytmusic login page."""
    path_parameters = event.get('pathParameters', {})
    user_id = path_parameters.get('userId')
    if not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'userId is required in path parameters'
            })
        }

    oauth_data =  _get_oauth_data()
    if not oauth_data:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error generating OAuth URL'
            })
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Redirecting to Google for authentication.',
                'data': oauth_data
            })
        }


def handle_poll_token_status(event):
    """Handle token polling for YouTube Music OAuth flow

        Args:
            event: Lambda event containing device_code and userId

        Returns:
            API Gateway response with appropriate status code and message
    """
    body = json.loads(event.get('body', '{}'))
    device_code = body.get('device_code')
    user_id = body.get('userId')

    if not device_code or not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'device_code and userId are required'
            })
        }

    try:
        oauth = _get_oauth()
        token = oauth.token_from_code(device_code)
        if isinstance(token, dict) and 'access_token' in token:
            _store_ytmusic_token(user_id, token)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Authentication successful',
                    'status': 'completed'
                })
            }
        if isinstance(token, dict) and token.get('error') == 'authorization_pending':
            return {
                'statusCode': 202,
                'body': json.dumps({
                    'message': 'Waiting for user authorization',
                    'status': 'pending'
                })
            }
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Invalid token response',
                'status': 'error',
                'details': str(token)
            })
        }
    except Exception as e:
        error_message = str(e).lower()

        if 'authorization_pending' in error_message:
            return {
                'statusCode': 202,
                'body': json.dumps({
                    'message': 'Waiting for user authorization',
                    'status': 'pending'
                })
            }
        elif 'expired' in error_message:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Device code has expired',
                    'status': 'expired'
                })
            }

# -------------------------------------------------------------------------------------

# Map routes to functions
operations = {
    'GET /ytmusic/isLoggedIn/{userId}': lambda event: handle_is_logged_in(event),
    'GET /ytmusic/login/{userId}': lambda event: handle_login_ytmusic(event),
    'POST /ytmusic/poll-token': lambda event: handle_poll_token_status(event),
}

def lambda_handler(event, context):
    """Main entry point for the AWS Lambda function."""
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': "http://localhost:5173",  # Update for production
        'Access-Control-Allow-Methods': 'OPTIONS, POST, GET, PUT, DELETE',
        'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token',
        'Access-Control-Expose-Headers': 'Authorization, X-Custom-Header',
        'Access-Control-Allow-Credentials': 'true'
    }

    # Handle OPTIONS requests
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }

    try:
        # Handle API Gateway routes
        route_key = f"{event['httpMethod']} {event['resource']}"
        if route_key in operations:
            response_body = operations[route_key](event)
            return {
                'statusCode': response_body['statusCode'],
                'body': response_body['body'],
                'headers': headers
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': f"Unsupported route: {route_key}"}),
                'headers': headers
            }
    except Exception as err:
        logger.error(f"Error: {str(err)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(err)})
        }
