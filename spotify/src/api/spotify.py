import json
import boto3
import spotipy
from datetime import datetime, timezone
from spotipy.oauth2 import SpotifyOAuth
from botocore.exceptions import ClientError
import logging

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

# Spotify configuration
SCOPE = "user-read-email, user-read-private, playlist-read-private, playlist-read-collaborative, user-library-read"
SPOTIPY_REDIRECT_URI = "http://localhost:5173/spotify/callback"
region_name = "eu-west-1"
secret_name = "Spotify"


def _get_secret():
    """
    Retrieve secret from AWS Secrets Manager.

    Returns:
        dict: Dictionary containing the secret values retrieved from AWS Secrets Manager
              with Spotify client credentials.

    Raises:
        ClientError: If there is an error retrieving the secret from AWS Secrets Manager.
    """
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        return json.loads(get_secret_value_response['SecretString'])
    except ClientError as e:
        logger.error(f"Error retrieving secret: {e}")
        raise e


def _store_spotify_token(userId, token_info):
    """Store Spotify tokens in DynamoDB.

    This function stores or updates Spotify authentication tokens for a given user in DynamoDB.
    It first checks if the user exists, then updates their record with the new token information.

    Args:
        userId (str): The unique identifier for the user
        token_info (dict): Dictionary containing Spotify token information with the following keys:
            - access_token: The Spotify access token
            - refresh_token: The Spotify refresh token
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

        # Update user record with Spotify tokens
        update_expression = """
            SET spotify_access_token = :access_token,
                spotify_refresh_token = :refresh_token,
                spotify_expires_in = :expires_in,
                spotify_token_type = :token_type,
                spotify_expires_at = :expires_at,
                spotify_token_updated = :updated_at
            """
        users_table.update_item(
            Key={'userid': userId},
            UpdateExpression=update_expression,
            ExpressionAttributeValues={
                ':access_token': token_info['access_token'],
                ':refresh_token': token_info['refresh_token'],
                ':expires_in': token_info['expires_in'],
                ':token_type': token_info['token_type'],
                ':expires_at': token_info['expires_at'],
                ':updated_at': int(datetime.now(timezone.utc).timestamp())
            }
        )
        logger.info(f"Stored tokens for user {userId}")
        return True
    except Exception as e:
        logger.error(f"Error storing tokens: {str(e)}")
        raise


def _get_spotify_tokens(userId):
    """Retrieve Spotify tokens from DynamoDB for the given user.

    Args:
        userId (str): The unique identifier for the user whose tokens to retrieve

    Returns:
        dict: Dictionary containing the user's Spotify tokens with keys:
            - spotify_access_token: The Spotify access token
            - spotify_expires_at: Timestamp when token expires
            - spotify_refresh_token: The Spotify refresh token
        None: If user is not found or there is an error accessing DynamoDB

    Raises:
        ClientError: If there is an error accessing DynamoDB
    """
    try:
        response = users_table.get_item(Key={'userid': userId},
                                        ProjectionExpression='spotify_access_token, spotify_expires_at, spotify_refresh_token')
        if 'Item' not in response:
            return None
        return response['Item']
    except ClientError as e:
        logger.error(f"Error accessing DynamoDB: {e.response['Error']['Message']}")
        return None


def _is_token_valid(userId):
    """Check and return valid Spotify access token for the user.

    This function validates the Spotify access token for a given user. It checks if:
    1. The user has stored tokens
    2. The access token exists and hasn't expired
    3. If expired, attempts to refresh using refresh token

    Args:
        userId (str): The unique identifier for the user

    Returns:
        str: Valid Spotify access token if found and valid
        None: If no valid token exists or refresh fails

    Raises:
        Exception: If there is an error validating the token
    """
    try:
        tokens = _get_spotify_tokens(userId)
        if not tokens:
            logger.info(f"No tokens found for user {userId}")
            return None

        current_time = int(datetime.now().timestamp())
        logger.info(f"Checking token validity for user {userId}")

        # Check if access token exists and is still valid
        if 'spotify_access_token' in tokens and 'spotify_expires_at' in tokens:
            try:
                expires_at = int(tokens['spotify_expires_at'])
                if expires_at > current_time:
                    logger.info(f"Valid token found for user {userId}")
                    return tokens['spotify_access_token']
                logger.info(f"Token expired for user {userId}")
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting expires_at to int: {str(e)}")
                return None

        # If token expired and refresh token exists, try to refresh
        if 'spotify_refresh_token' in tokens:
            logger.info(f"Attempting to refresh token for user {userId}")
            return _refresh_spotify_token(userId, tokens['spotify_refresh_token'])

        logger.info(f"No refresh token found for user {userId}")
        return None

    except Exception as e:
        logger.error(f"Error validating token for user {userId}: {str(e)}")
        return None


def _refresh_spotify_token(userId, refresh_token):
    """Refresh Spotify access token using the refresh token.

    This function attempts to refresh an expired Spotify access token using the stored refresh token.
    It updates the user's token information in DynamoDB with the new access token and expiration time.

    Args:
        userId (str): The unique identifier for the user whose token to refresh
        refresh_token (str): The Spotify refresh token to use for getting a new access token

    Returns:
        str: The new Spotify access token if refresh was successful
        None: If there was an error refreshing the token or updating DynamoDB

    Raises:
        ClientError: If there is an error accessing DynamoDB
    """
    try:
        new_token_info = _get_spotify_service().auth_manager.refresh_access_token(refresh_token)
        logger.info(f"new token info: {new_token_info}")

        update_expression = 'SET spotify_access_token = :token, spotify_expires_at = :exp, spotify_token_updated = :updated'
        expression_values = {
            ':token': new_token_info['access_token'],
            ':exp': int(new_token_info['expires_at']),
            ':updated': int(datetime.now().timestamp())
        }

        # If a new refresh token is provided, update it
        if 'refresh_token' in new_token_info:
            update_expression += ', spotify_refresh_token = :refresh'
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


def _get_spotify_service():
    """Get Spotify service instance with valid tokens.

    This function creates and returns a Spotify service instance with proper authentication.
    It retrieves client credentials from AWS Secrets Manager and sets up OAuth authentication.

    Returns:
        spotipy.Spotify: Authenticated Spotify client instance with valid tokens

    Raises:
        KeyError: If required Spotify credentials are missing from secrets
        Exception: If there is an error creating the Spotify service
    """
    try:
        # Get secrets from AWS Secrets Manager
        secrets = _get_secret()

        # Validate required secrets exist
        if not all(key in secrets for key in ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET"]):
            logger.error("Missing required Spotify credentials in secrets")
            raise KeyError("Missing required Spotify credentials")

        # Create OAuth manager
        auth_manager = SpotifyOAuth(
            client_id=secrets["SPOTIPY_CLIENT_ID"],
            client_secret=secrets["SPOTIPY_CLIENT_SECRET"],
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=SCOPE,
            open_browser=True,
            show_dialog=True,
            cache_handler=spotipy.MemoryCacheHandler()
        )

        # Create and return Spotify client
        return spotipy.Spotify(auth_manager=auth_manager)
    except KeyError as e:
        logger.error(f"Missing required secrets: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating Spotify service: {str(e)}")
        raise


def _exchange_code_for_token(code):
    """Exchange the authorization code for Spotify access and refresh tokens.

    This function takes the authorization code received from Spotify's OAuth flow and
    exchanges it for access and refresh tokens using the Spotify auth manager.
    The tokens are cached by the auth manager for future use.

    Args:
        code (str): The authorization code received from Spotify OAuth callback

    Returns:
        dict: Token information containing access_token, refresh_token, expires_at etc if successful
        None: If there was an error exchanging the code for tokens

    Raises:
        spotipy.SpotifyOauthError: If there is an error in the OAuth token exchange
        Exception: For any other unexpected errors during token exchange
    """
    try:
        auth_manager = _get_spotify_service().auth_manager
        auth_manager.get_access_token(code=code, as_dict=False, check_cache=True)  # This caches the token
        token_info = auth_manager.get_cached_token()  # Get the cached token info
        logger.info(token_info)
        return token_info
    except spotipy.SpotifyOauthError as e:
        logger.error(f"OAuth error during token exchange: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token exchange: {str(e)}")
        return None


def _get_playlists(access_token):
    """Fetch user's playlists from Spotify.

    This function retrieves all playlists for the authenticated user from Spotify,
    handling pagination to get the complete list.

    Args:
        access_token (str): Valid Spotify access token for authentication

    Returns:
        dict: Dictionary containing:
            - items (list): List of playlist objects from Spotify
            - total (int): Total number of playlists
        None: If there was an error fetching the playlists

    Raises:
        spotipy.SpotifyException: If there is an error calling the Spotify API
        Exception: For any other unexpected errors
    """
    try:
        spotify_client = spotipy.Spotify(access_token)
        # Fetch all playlists with pagination
        playlists = []
        offset = 0
        limit = 50  # Spotify's maximum limit per request

        while True:
            response = spotify_client.current_user_playlists(limit=limit, offset=offset)

            if not response or 'items' not in response:
                logger.error("Invalid response format from Spotify API")
                return None

            playlists.extend(response['items'])

            # Check if we've fetched all playlists
            if len(response['items']) < limit or response['next'] is None:
                break

            offset += limit

        logger.info(f"Successfully fetched {len(playlists)} playlists")
        return {
            'items': playlists,
            'total': len(playlists)
        }
    except spotipy.SpotifyException as e:
        logger.error(f"Spotify API error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching playlists: {str(e)}")
        return None


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


def handle_login_spotify(event):
    """Handle Spotify login and redirect the user to the Spotify login page.

    This function validates the user ID and generates a Spotify authorization URL
    that the user can be redirected to for authentication.

    Args:
        event (dict): The API Gateway event object containing the request details
                     including pathParameters with userId

    Returns:
        dict: Response object containing:
            - statusCode (int): HTTP status code (200 for success, 400 for invalid request)
            - body (str): JSON string containing:
                - message (str): Description of the response
                - url (str): Spotify authorization URL for redirect

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

    authorize_url = _get_spotify_service().auth_manager.get_authorize_url()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Redirecting to Spotify for authentication.',
            'url': authorize_url
        })
    }


# TODO: Fix callback - current problem - Failed to exchange authorization code: error: invalid_grant, error_description: Invalid authorization code - but it works and stores the token.
def handle_spotify_callback(event):
    """Handle the callback from Spotify after user authentication.

    This function processes the callback request from Spotify after a user has authenticated.
    It extracts the authorization code and user ID from the request, exchanges the code for
    an access token, and stores the token information.

    Args:
        event (dict): The API Gateway event object containing:
            - body (str): JSON string with:
                - code (str): Authorization code from Spotify
                - userId (str): ID of the user being authenticated

    Returns:
        dict: Response object containing:
            - statusCode (int): HTTP status code (200 for success)
            - body (str): JSON string with:
                - message (str): Success/failure message
                - isLoggedIn (bool): True if authentication successful
            OR
            - error (str): Error message if authentication failed

    Raises:
        json.JSONDecodeError: If request body contains invalid JSON
        Exception: For any other unexpected errors during token exchange
    """
    try:
        body = json.loads(event.get('body', '{}'))
        code = body.get('code')
        user_id = body.get('userId')

        if not code:
            return {'error': 'Authorization code not found in request body'}

        token_info = _exchange_code_for_token(code)
        _store_spotify_token(user_id, token_info)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Authentication successful',
                'isLoggedIn': True
            })
        }
    except json.JSONDecodeError:
        return {'error': 'Invalid JSON in request body'}
    except Exception as e:
        logger.error(f'Failed to exchange authorization code: {str(e)}')
        return {'error': f'Failed to exchange authorization code: {str(e)}'}


def handle_get_user_playlists(event):
    """Handle request to fetch user's Spotify playlists.

    This function retrieves all playlists for a given user from their Spotify account.
    It validates the user ID and access token before making the request to Spotify's API.

    Args:
        event (dict): The API Gateway event object containing:
            - pathParameters (dict): Contains userId for the request

    Returns:
        dict: Response object containing:
            - statusCode (int): HTTP status code (200 for success, 400-500 for errors)
            - body (str): JSON string containing:
                - message (str): Description of the response
                - playlists (list): List of playlist objects if successful
                - error (str): Error message if request failed

    Raises:
        None: All exceptions are caught and returned as error responses
    """
    try:
        # Extract and validate user ID
        path_parameters = event.get('pathParameters', {})
        userId = path_parameters.get('userId')
        if not userId:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'userId is required in path parameters'
                })
            }

        # Validate token
        access_token = _is_token_valid(userId)
        if not access_token:
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'message': 'Invalid or expired token'
                })
            }

        playlists = _get_playlists(access_token)

        if not playlists or 'items' not in playlists:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': 'No playlists found'
                })
            }

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully retrieved playlists',
                'playlists': playlists['items']
            })
        }
    except spotipy.SpotifyException as e:
        logger.error(f"Spotify API error: {str(e)}")
        return {
            'statusCode': e.http_status if hasattr(e, 'http_status') else 500,
            'body': json.dumps({
                'message': 'Error accessing Spotify API',
                'error': str(e)
            })
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'error': str(e)
            })
        }


# -------------------------------------------------------------------------------------

# Map routes to functions
operations = {
    'GET /spotify/isLoggedIn/{userId}': lambda event: handle_is_logged_in(event),
    'GET /spotify/login/{userId}': lambda event: handle_login_spotify(event),
    'POST /spotify/callback': lambda event: handle_spotify_callback(event),
    'GET /spotify/playlists/{userId}': lambda event: handle_get_user_playlists(event),

}


def lambda_handler(event, context):
    """Main entry point for the AWS Lambda function.

    This function handles all incoming API Gateway requests, including CORS preflight
    requests (OPTIONS) and routing to the appropriate handler function based on the
    HTTP method and resource path.

    Args:
        event (dict): The API Gateway event object containing request details including:
            - httpMethod (str): The HTTP method (GET, POST, OPTIONS etc)
            - resource (str): The API resource path
            - body (str): Request body for POST/PUT requests
            - pathParameters (dict): URL path parameters
        context (LambdaContext): AWS Lambda context object providing runtime information

    Returns:
        dict: Response object containing:
            - statusCode (int): HTTP status code (200 for success, 4xx/5xx for errors)
            - headers (dict): Response headers including CORS headers
            - body (str): JSON response body

    Raises:
        None: All exceptions are caught and returned as error responses
    """
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
