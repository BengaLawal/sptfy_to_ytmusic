import json
import os
from datetime import datetime, timezone

import boto3
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from botocore.exceptions import ClientError

# Add DynamoDB setup
USERS_TABLE = os.environ['USERS_TABLE']
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USERS_TABLE)

SCOPE = "user-read-email, user-read-private, playlist-read-private, playlist-read-collaborative, user-library-read"
SPOTIPY_REDIRECT_URI="http://localhost:5173/spotify-callback"
region_name = "eu-west-1"
secret_name = "Spotify"

def get_secret(region, secret_id):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_id
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e
    return json.loads(get_secret_value_response['SecretString'])

def get_spotify_service():
    # Retrieve secrets
    secrets = get_secret(region_name, secret_name)
    spotipy_client_id=secrets["SPOTIPY_CLIENT_ID"]
    spotipy_client_secret=secrets["SPOTIPY_CLIENT_SECRET"]

    # Replace with your own Client ID, Client Secret, and Redirect URI
    return spotipy.Spotify(auth_manager=SpotifyOAuth(client_id= spotipy_client_id,
                                                     client_secret=spotipy_client_secret,
                                                     redirect_uri=SPOTIPY_REDIRECT_URI,
                                                     scope=SCOPE,
                                                     open_browser=True,
                                                     show_dialog=True,
                                                     ))

def store_spotify_token(user_id, token_info):
    try:
        # Update user record with Spotify tokens
        update_expression = """
            SET access_token = :access_token,
                refresh_token = :refresh_token,
                expires_in = :expires_in,
                token_type = :token_type,
                expires_at = :expires_at,
                spotify_token_updated = :updated_at
            """

        users_table.update_item(
            Key={'userid': user_id},
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
        return True
    except Exception as e:
        print(f"Error storing tokens: {str(e)}")
        raise

# Handle Spotify login
def login_spotify():
    # This will redirect the user to the Spotify login page
    authorize_url = get_spotify_service().auth_manager.get_authorize_url()
    return {
        'message': 'Redirecting to Spotify for authentication.',
        'url': authorize_url
    }

def handle_spotify_callback(event):
    try:
        # Get the authorization code from request body
        body = json.loads(event.get('body', '{}'))
        code = body.get('code')
        user_id = body.get('userId')

        if not code:
            return {
                'error': 'Authorization code not found in request body'
            }

        # Exchange the code for tokens using the auth manager
        token_info = get_spotify_service().auth_manager.get_access_token(code)
        store_spotify_token(user_id, token_info)

        return {
            'message': 'Authentication successful',
            'access_token': token_info['access_token'],
            'token_type': token_info['token_type'],
            'expires_in': token_info['expires_in'],
            'refresh_token': token_info['refresh_token'],
            'expires_at': token_info['expires_at']
        }
    except json.JSONDecodeError:
        return {
            'error': 'Invalid JSON in request body'
        }
    except Exception as e:
        return {
            'error': f'Failed to exchange authorization code: {str(e)}'
        }

# Get current user's playlists and ids
def get_playlists():
    results = get_spotify_service().current_user_playlists()
    # results = get_spotify_service().current_user_playlists()
    return { item['name']:item['id'] for item in results['items']}



# Map routes to functions
operations = {
    'GET /login-spotify': lambda event: login_spotify(),
    'POST /spotify-callback': lambda event: handle_spotify_callback(event),
    'GET /playlists': lambda event: get_playlists(),
}

def lambda_handler(event, context):
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
                'statusCode': 200,
                'body': json.dumps(response_body),
                'headers': headers
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': f"Unsupported route: {route_key}"}),
                'headers': headers
            }
    except Exception as err:
        print(f"Error: {str(err)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(err)})
        }
