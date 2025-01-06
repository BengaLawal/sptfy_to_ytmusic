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
SPOTIPY_REDIRECT_URI="http://localhost:5173/spotify/callback"
region_name = "eu-west-1"
secret_name = "Spotify"

def _get_secret():
    """Retrieve secret from AWS Secrets Manager."""
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        return json.loads(get_secret_value_response['SecretString'])
    except ClientError as e:
        logger.error(f"Error retrieving secret: {e}")
        raise e

def _store_spotify_token(userId, token_info):
    """Store Spotify tokens in DynamoDB."""
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
    """Retrieve Spotify tokens from DynamoDB for the given user."""
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
    """Check and return valid Spotify access token for the user."""
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
    """Refresh Spotify access token using the refresh token."""
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
    """Get Spotify service instance with valid tokens."""
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
    """Exchange the code for tokens using the auth manager"""
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
    """    Fetch user's playlists from Spotify"""
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
    """Handle the request to check if the user is logged in."""
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
    """ Handle Spotify login and redirect the user to the Spotify login page."""
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
    """Handle the callback from Spotify after user authentication."""
    try:
        body = json.loads(event.get('body', '{}'))
        code = body.get('code')
        userId = body.get('userId')

        if not code:
            return {'error': 'Authorization code not found in request body'}

        token_info = _exchange_code_for_token(code)
        _store_spotify_token(userId, token_info)
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

# dummy_event = {
#     'pathParameters': {
#         'userId': '32950464-7091-70a7-0119-5c35cb36052a'
#     },
#
# }
# print(handle_is_logged_in(dummy_event))

# testEvent = {
#     "body":json.dumps({
#         "code": "AQAp41KELzLv_VU1w4beBbYqhzomYLIgtQ-HXbs9eMGdkLjFI1gMdP8eDWt0rQpCmffxzBG3YXMbB1oXV7Ygs0B7WoRDvm0p1b-EfvYpqU1I3EC83RcBA64BCkbhyPN6oimwXnzHGdsCF0PqU9Os4oN0m09u01lSLSbGwNhSz_4j0GgMLJ4sr6bZxjrzbNoJwaN2YYLy37yaTxCT2tWtO8tFJZwytMZGzber-gPMxPFFDoR35V35iJYsv_KKIGSdRMsRaDAXH3VKpB3zn_2FrgWPGgcPRU_4akwWjHzOTmAphxV82COA_7nHdqbRCj1OLOSh64M",
#         "userId": "42457444-1001-7051-3dd4-ef84241184ea"
#     }),
# }
# handle_spotify_callback(testEvent)

# print(handle_get_user_playlists(dummy_event))

# -------------------------------------------------------------------------------------

# Map routes to functions
operations = {
    'GET /spotify/isLoggedIn/{userId}': lambda event: handle_is_logged_in(event),
    'GET /spotify/login/{userId}': lambda event: handle_login_spotify(event),
    'POST /spotify/callback': lambda event: handle_spotify_callback(event),
    'GET /spotify/playlists/{userId}': lambda event: handle_get_user_playlists(event),

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
