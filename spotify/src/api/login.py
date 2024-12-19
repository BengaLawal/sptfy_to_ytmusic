import json
import os
import boto3
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from botocore.exceptions import ClientError

SCOPE = "user-read-email, user-read-private, playlist-read-private, playlist-read-collaborative, user-library-read"
SPOTIPY_REDIRECT_URI="http://localhost:8888/callback"
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

    # # Remove existing cache file
    # if os.path.exists(".cache"):
    #     os.remove(".cache")

    # Replace with your own Client ID, Client Secret, and Redirect URI
    return spotipy.Spotify(auth_manager=SpotifyOAuth(client_id= spotipy_client_id,
                                                     client_secret=spotipy_client_secret,
                                                     redirect_uri=SPOTIPY_REDIRECT_URI,
                                                     scope=SCOPE,
                                                     open_browser=True,
                                                     show_dialog=True,
                                                     ))
# Handle Spotify login
def login_spotify():
    # This will redirect the user to the Spotify login page
    sp = get_spotify_service()
    return {
        'message': 'Redirecting to Spotify for authentication.',
        'url': SPOTIPY_REDIRECT_URI
    }

# Get current user's playlists and ids
def get_playlists():
    results = get_spotify_service().current_user_playlists()
    return { item['name']:item['id'] for item in results['items']}

# Map routes to functions
operations = {
    'GET /login-spotify': lambda event: login_spotify(),  # New route for Spotify login
    'GET /playlists': lambda event: get_playlists(),
}

# print(get_playlists())

def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT,DELETE',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        "Access-Control-Expose-Headers": "Authorization, X-Custom-Header",
        "Access-Control-Allow-Credentials": "true"
    }

    try:
        # Handle API Gateway routes
        route_key = f"{event['httpMethod']} {event['resource']}"
        if route_key in operations:
            response_body = operations[route_key](event)
            status_code = 200
        else:
            raise ValueError(f"Unsupported route: {route_key}")
    except Exception as err:
        response_body = {'Error': str(err)}
        status_code = 400
        print(str(err))

    return {
        'statusCode': status_code,
        'body': json.dumps(response_body),
        'headers': headers
    }
