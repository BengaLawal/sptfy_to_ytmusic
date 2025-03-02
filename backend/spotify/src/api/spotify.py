import json
import uuid
from datetime import datetime, timezone

import spotipy
import logging
import boto3
from config import SpotifyConfig
from spotipy.oauth2 import SpotifyOAuth
from shared_utils.dynamodb import DynamoDBService
from shared_utils.secrets_manager import get_secret
from shared_utils.token_validator import is_token_valid

config_ = SpotifyConfig()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

db_service = DynamoDBService(config_.USERS_TABLE, config_.TRANSFER_TABLE)


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
        secrets = get_secret(config_.REGION_NAME, config_.SECRET_NAME)

        # Validate required secrets exist
        if not all(key in secrets for key in ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET"]):
            logger.error("Missing required Spotify credentials in secrets")
            raise KeyError("Missing required Spotify credentials")

        # Create OAuth manager
        auth_manager = SpotifyOAuth(
            client_id=secrets["SPOTIPY_CLIENT_ID"],
            client_secret=secrets["SPOTIPY_CLIENT_SECRET"],
            redirect_uri=config_.REDIRECT_URI,
            scope=config_.SCOPE,
            open_browser=True,
            show_dialog=True,
            cache_handler=spotipy.MemoryCacheHandler()
        )
        return spotipy.Spotify(auth_manager=auth_manager)
    except Exception as e:
        logger.error(f"Error creating Spotify service: {str(e)}")
        raise


def _refresh_spotify_token(user_id, refresh_token):
    """Refresh Spotify access token using the refresh token.

    This function attempts to refresh an expired Spotify access token using the stored refresh token.
    It updates the user's token information in DynamoDB with the new access token and expiration time.

    Args:
        user_id (str): The unique identifier for the user whose token to refresh
        refresh_token (str): The Spotify refresh token to use for getting a new access token

    Returns:
        str: The new Spotify access token if refresh was successful
        None: If there was an error refreshing the token or updating DynamoDB

    Raises:
        ClientError: If there is an error accessing DynamoDB
    """
    try:
        new_token_info = _get_spotify_service().auth_manager.refresh_access_token(refresh_token)
        if db_service.update_token(user_id, new_token_info, config_.SERVICE_PREFIX):
            return new_token_info['access_token']
        return None
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        return None

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
        return auth_manager.get_cached_token()  # Get the cached token info
    except Exception as e:
        logger.error(f"Error exchanging code for token: {str(e)}")
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
        playlists = []
        offset = 0
        limit = 50

        while True:
            response = spotify_client.current_user_playlists(limit=limit, offset=offset)
            if not response or 'items' not in response:
                return None

            playlists.extend(response['items'])
            # Check if we've fetched all playlists
            if len(response['items']) < limit or response['next'] is None:
                break
            offset += limit
        return {
            'items': playlists,
            'total': len(playlists)
        }
    except Exception as e:
        logger.error(f"Error fetching playlists: {str(e)}")
        return None


def _get_playlist_tracks(spotify_client, playlist_id, access_token):
    """Fetch all tracks from a Spotify playlist with batch processing.

    Args:
        spotify_client: Authenticated Spotify client
        playlist_id (str): Spotify playlist ID
        access_token (str): Valid Spotify access token

    Returns:
        list: List of track objects with essential info
    """
    try:
        playlist_details = spotify_client.playlist(playlist_id)
        playlist_name = playlist_details['name']

        tracks = []
        offset = 0
        limit = 100  # Spotify's maximum limit per request

        while True:
            response = spotify_client.playlist_items(
                playlist_id,
                offset=offset,
                limit=limit,
                fields='items(track(name,artists(name),duration_ms)),total,next',
                additional_types=['track']
            )

            if not response or 'items' not in response:
                break

            # Extract just the needed track info
            for item in response['items']:
                if item['track']:  # Check if track exists (could be None for deleted tracks)
                    track = item['track']
                    tracks.append({
                        'name': track['name'],
                        'artists': [artist['name'] for artist in track['artists']],
                        'duration_ms': track['duration_ms']
                    })

            if not response.get('next'):
                break

            offset += limit

        return playlist_name, tracks
    except Exception as e:
        logger.error(f"Error fetching playlist tracks: {str(e)}")
        raise


def _publish_to_sns(sns_data):
    try:
        sns_client = boto3.client('sns')
        response = sns_client.publish(
            TopicArn=config_.PLAYLIST_TRANSFER_TOPIC,
            Message=json.dumps(sns_data)
        )
        logger.info(f"Published to SNS: {response}")

        # Check if the publish was successful (SNS returns a 200 status code)
        if response and 'MessageId' in response:
            return True
        return False
    except Exception as e:
        logger.error(f"Error publishing to SNS: {str(e)}")
        return False


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
    user_id = path_parameters.get('userId')
    if not user_id:
        logger.info(f"Missing userId in path parameters")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'userId is required in path parameters'
            })
        }

    logger.info(f"Checking login status for user {user_id}")
    access_token = is_token_valid(db_service, user_id, config_.SERVICE_PREFIX, _refresh_spotify_token)
    if access_token:
        logger.info(f"User {user_id} is logged in")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'User is logged in',
                'isLoggedIn': True,
            })
        }
    else:
        logger.info(f"User {user_id} is not logged in")
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
    user_id = path_parameters.get('userId')
    if not user_id:
        logger.info("Missing userId in path parameters")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'userId is required in path parameters'
            })
        }

    logger.info(f"Generating Spotify authorization URL for user {user_id}")
    authorize_url = _get_spotify_service().auth_manager.get_authorize_url()
    logger.info(f"Redirecting user {user_id} to Spotify login")
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

        logger.info(f"Processing Spotify callback for user {user_id}")

        if not code:
            return {'error': 'Authorization code not found in request body'}

        token_info = _exchange_code_for_token(code)
        db_service.store_tokens(user_id, token_info, config_.SERVICE_PREFIX)
        logger.info(f"Successfully authenticated Spotify for user {user_id}")
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
        user_id = path_parameters.get('userId')
        logger.info(f"Fetching playlists for user {user_id}")

        if not user_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'userId is required in path parameters'
                })
            }

        # Validate token
        access_token = is_token_valid(db_service, user_id, config_.SERVICE_PREFIX, _refresh_spotify_token)
        if not access_token:
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'message': 'Invalid or expired token'
                })
            }

        playlists = _get_playlists(access_token)

        if not playlists or 'items' not in playlists:
            logger.info(f"No playlists found for user {user_id}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': 'No playlists found'
                })
            }

        logger.info(f"Successfully retrieved {len(playlists['items'])} playlists for user {user_id}")
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


def handle_transfer_to_ytmusic(event):
    """Handle the request to transfer selected playlists from Spotify to YouTube Music."""
    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('userId',  None)
        playlist_ids = body.get('playlistIds', [])

        # Generate unique transfer ID
        transfer_id = str(uuid.uuid4())

        # Create initial transfer record
        transfer_details = {
            'transfer_id': transfer_id,
            'user_id': user_id,
            'timestamp_started': int(datetime.now(timezone.utc).timestamp()),
            'status': 'in_progress',
            'total_playlists': len(playlist_ids),
            'total_tracks': 0,
            'completed_playlists': 0,
            'completed_tracks': 0,
            'failed_playlists': 0,
            'failed_tracks': 0,
            'playlists': [],
            'error_details': None
        }

        try:
            db_service.update_transfer_details(transfer_id, transfer_details)
            logger.info(f"Initial transfer record created for transfer ID {transfer_id}")
        except Exception as e:
            logger.error(f"Failed to create initial transfer record for transfer ID {transfer_id}: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Failed to initiate transfer process'
                })
            }


        logger.info(f"Starting playlist transfer for user {user_id}, playlists: {playlist_ids}")

        if not user_id or not playlist_ids:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'userId and playlistIds are required in path parameters'
                })
            }

        access_token = is_token_valid(db_service, user_id, config_.SERVICE_PREFIX, _refresh_spotify_token)
        if not access_token:
            return {
                'statusCode': 401,
                'body': json.dumps({
                    'message': 'Invalid or expired token'
                })
            }

        spotify_client = spotipy.Spotify(auth=access_token)

        # Collect all playlists' details
        all_playlists_data = []

        for playlist_id in playlist_ids:
            logger.info(f"Fetching tracks for playlist {playlist_id}")
            playlist_name, tracks = _get_playlist_tracks(spotify_client, playlist_id, access_token)

            if tracks:
                all_playlists_data.append({
                    'playlist_id': playlist_id,
                    'playlist_name': playlist_name,
                    'tracks': tracks
                })

        # Publish to SNS for async processing with all playlists' data
        if all_playlists_data:
            sns_data = {
                'transfer_id': transfer_id,
                'playlists_data': all_playlists_data,
                'user_id': user_id
            }
            sns_published = _publish_to_sns(sns_data)
            if not sns_published:
                logger.info(f"Failed to publish SNS message for user {user_id}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({'message': 'Failed to initiate transfer process'})
                }

        logger.info(f"Successfully initiated transfer for {len(all_playlists_data)} playlists")
        return {
            'statusCode': 200,
            'body' : json.dumps({
                'message': 'Transfer initiated successfully',
                'transfer_id': transfer_id
            })
        }
    except Exception as e:
        logger.error(f"Error in handle_get_playlist_tracks: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'error': str(e)
            })
        }

def handle_transfer_status(event):
    body = json.loads(event.get('body', '{}'))
    transfer_id = body.get('transfer_id')
    user_id = body.get('user_id')

    transfer_details = db_service.get_transfer_details(transfer_id)
    return {
        'statusCode': 200,
        'body': json.dumps(transfer_details)
    }


# -------------------------------------------------------------------------------------

# Map routes to functions
operations = {
    'GET /spotify/isLoggedIn/{userId}': lambda event: handle_is_logged_in(event),
    'GET /spotify/login/{userId}': lambda event: handle_login_spotify(event),
    'POST /spotify/callback': lambda event: handle_spotify_callback(event),
    'GET /spotify/playlists/{userId}': lambda event: handle_get_user_playlists(event),
    'POST /transfer/sptfy-to-ytmusic': lambda event: handle_transfer_to_ytmusic(event),
    'POST /transfer/status' : lambda event: handle_transfer_status(event)
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
        'Access-Control-Allow-Origin': config_.ACCESS_CONTROL_ALLOW_ORIGIN,
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
