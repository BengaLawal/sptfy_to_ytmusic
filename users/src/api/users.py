import json
import os
import uuid
from datetime import datetime
import boto3
from decimal import Decimal

# Prepare DynamoDB client
USERS_TABLE = os.getenv('USERS_TABLE', None)
dynamodb = boto3.resource('dynamodb')
ddbTable = dynamodb.Table(USERS_TABLE)


# Utility function to handle Decimal
def convert_decimal(obj):
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj

# Functions for CRUD operations
def get_users():
    response = ddbTable.scan(Select='ALL_ATTRIBUTES')
    return response['Items']

def get_user_by_id(user_id):
    response = ddbTable.get_item(Key={'userid': user_id})
    return response.get('Item', {})

def delete_user(user_id):
    ddbTable.delete_item(Key={'userid': user_id})
    return {}

def create_user(event):
    request_json = json.loads(event['body'])
    request_json['timestamp'] = datetime.now().isoformat()
    # generate unique id if it isn't present in the request
    if 'userid' not in request_json:
        request_json['userid'] = str(uuid.uuid1())
    # update the database
    ddbTable.put_item(
        Item=request_json
    )
    return request_json

def update_user(user_id, request_body):
    user_data = {
        'userid': user_id,
        'timestamp': datetime.now().isoformat(),
        **request_body
    }
    ddbTable.put_item(Item=user_data)
    return user_data

def handle_cognito_post_confirmation(user_attributes):
    user_data = {
        'userid': user_attributes.get('sub'),
        'email': user_attributes.get('email'),
        'name': user_attributes.get('name'),
        'timestamp': datetime.now().isoformat()
    }
    ddbTable.put_item(Item=user_data)
    return user_data

# Map routes to functions
operations = {
    'GET /users': lambda event: get_users(),
    'GET /users/{userid}': lambda event: get_user_by_id(event['pathParameters']['userid']),
    'DELETE /users/{userid}': lambda event: delete_user(event['pathParameters']['userid']),
    'POST /users': lambda event: create_user(
        event
    ),
    'PUT /users/{userid}': lambda event: update_user(
        event['pathParameters']['userid'], json.loads(event['body'])
    ),
    'PostConfirmation_ConfirmSignUp': lambda event: handle_cognito_post_confirmation(
        event['request']['userAttributes']
    ),
}

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
        # Handle PostConfirmation trigger
        if event.get('triggerSource') == 'PostConfirmation_ConfirmSignUp':
            operations[event['triggerSource']](event)
            return event
        else:
            # Handle API Gateway routes
            route_key = f"{event['httpMethod']} {event['resource']}"
            if route_key in operations:
                response_body = operations[route_key](event)
                response_body = convert_decimal(response_body)
                status_code = 200
            else:
                raise ValueError(f"Unsupported route: {route_key}")
    except Exception as err:
        response_body = {'Error': str(err)}
        status_code = 400
        print(str(err))

    return {
        'statusCode': status_code,
        'body': json.dumps(convert_decimal(response_body)),
        'headers': headers
    }