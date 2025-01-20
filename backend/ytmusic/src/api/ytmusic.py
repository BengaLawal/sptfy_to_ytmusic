import json
import logging
import time

from ytmusicapi import YTMusic
from config import YTMusicConfig
from ytmusicapi.auth.oauth import OAuthCredentials
from shared_utils.dynamodb import DynamoDBService
from shared_utils.secrets_manager import get_secret
from shared_utils.token_validator import is_token_valid

config_ = YTMusicConfig()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

db_service = DynamoDBService(config_.USERS_TABLE)


def _get_oauth():
    secrets = get_secret(config_.REGION_NAME, config_.SECRET_NAME)
    return OAuthCredentials(
        client_id=secrets['YTMUSIC_CLIENT_ID'],
        client_secret=secrets['YTMUSIC_CLIENT_SECRET'],
    )


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


def _refresh_ytmusic_token(user_id, refresh_token):
    """Refresh YtMusic access token using the refresh token.

    This function attempts to refresh an expired YtMusic access token using the stored refresh token.
    It updates the user's token information in DynamoDB with the new access token and expiration time.

    Args:
        user_id (str): The unique identifier for the user whose token to refresh
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
        if db_service.update_token(user_id, new_token_info, config_.SERVICE_PREFIX):
            return new_token_info['access_token']
        return None
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        return None


def _create_ytmusic_playlist(ytmusic_client, playlist_name, description=""):
    """Create a new YouTube Music playlist.

    Args:
        ytmusic_client: Authenticated YTMusic client
        playlist_name (str): Name for the new playlist
        description (str): Optional playlist description

    Returns:
        str: ID of the created playlist
    """
    try:
        return ytmusic_client.create_playlist(
            title=playlist_name,
            description=description,
            privacy_status='PRIVATE'  # Start as private for safety
        )
    except Exception as e:
        logger.error(f"Error creating YouTube Music playlist: {str(e)}")
        raise


def _search_and_add_tracks(ytmusic_client, playlist_id, tracks, batch_size=50):
    """Search for tracks on YouTube Music and add them to playlist with batch processing.

    Args:
        ytmusic_client: Authenticated YTMusic client
        playlist_id (str): YouTube Music playlist ID
        tracks (list): List of track objects from Spotify
        batch_size (int): Number of tracks to process in each batch

    Returns:
        dict: Summary of transfer results
    """
    results = {
        'successful': 0,
        'failed': 0,
        'not_found': 0
    }

    for i in range(0, len(tracks), batch_size):
        batch = tracks[i:i + batch_size]
        for track in batch:
            try:
                # Create search query from track info
                query = f"{track['name']} {' '.join(track['artists'])}"
                search_results = ytmusic_client.search(query, filter='songs', limit=1)

                if search_results and len(search_results) > 0:
                    video_id = search_results[0]['videoId']
                    ytmusic_client.add_playlist_items(playlist_id, [video_id])
                    results['successful'] += 1
                else:
                    results['not_found'] += 1

                # Add small delay to respect rate limits
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error adding track {track['name']}: {str(e)}")
                results['failed'] += 1

    return results

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
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'userId is required in path parameters'
            })
        }

    access_token = is_token_valid(db_service, user_id, config_.SERVICE_PREFIX, _refresh_ytmusic_token)
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
            db_service.store_tokens(user_id, token, config_.SERVICE_PREFIX)
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


def handle_spotify_sns_message(event, context):
    """Handle SNS messages for playlist transfer."""
    logger.info(event)
    for record in event['Records']:
        message = json.loads(record['Sns']['Message'])
        user_id = message['user_id']
        playlists = message['playlists']

        access_token = is_token_valid(db_service, user_id, config_.SERVICE_PREFIX, _refresh_ytmusic_token)
        if not access_token:
            logger.error("Invalid or expired YouTube Music token")
            continue  # Skip processing if token is invalid

        ytmusic_client = YTMusic(auth=access_token)

        for playlist in playlists:
            playlist_name = playlist['playlist_name']
            tracks = playlist['tracks']

            try:
                # Create the playlist in YouTube Music
                created_playlist_id = _create_ytmusic_playlist(ytmusic_client, playlist_name)

                # Search for tracks and add them to the created playlist
                transfer_results = _search_and_add_tracks(ytmusic_client, created_playlist_id, tracks)

                logger.info(f"Transfer results for playlist '{playlist_name}': {transfer_results}")

            except Exception as e:
                logger.error(f"Error processing playlist '{playlist_name}': {str(e)}")

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
