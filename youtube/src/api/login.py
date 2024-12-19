import os
import time
import json
import logging
from subprocess import Popen, PIPE
from flask import Flask, Response, jsonify
from typing import Dict, Any

app = Flask(__name__)
oauth_file: str = "oauth.json"
PORT: int = 5001

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/c', methods=['GET'])
def login() -> [Response, int]:
    logging.info("Received request to initiate YouTube login flow.")
    if is_logged_in(oauth_file):
        logging.info("OAuth file exists. User is already logged in.")
        return jsonify({"message": "Already logged in"}), 200

    return initiate_oauth_flow()

@app.route('/make_playlist', methods=['GET'])
def make_playlist():
    pass


def is_logged_in(file_path: str) -> bool:
    """
    Check if the user is logged in by verifying the existence of the OAuth file
    and ensuring the token has not expired.

    Args:
        file_path (str): Path to the OAuth file.

    Returns:
        bool: True if the user is logged in and the token is valid, False otherwise.
    """
    if os.path.isfile(file_path):
        try:
            with open(file_path, 'r') as file:
                oauth_data: Dict[str, Any] = json.load(file)

            current_time: float = time.time()
            if current_time < oauth_data.get("expires_at", 0):
                return True
        except Exception as e:
            logging.error(f"Failed to read or parse oauth.json: {e}")

    return False


def initiate_oauth_flow() -> [Response, int]:
    """
    Start the OAuth flow for YouTube Music by running the command to authenticate the user.

    Returns:
        Response: Flask response with the result of the OAuth process.
    """
    try:
        logging.info("Starting ytmusicapi OAuth flow.")
        process: Popen = start_oauth_process()

        wait_for_user_interaction()

        # Simulate pressing Enter to proceed with the oauth.json creation
        send_enter_key_to_process(process)

        # Allow time for oauth.json to be generated
        logging.info("Waiting for 10 seconds to give time for oauth.json to be created.")
        time.sleep(10)

        if os.path.exists(oauth_file):
            message = "oauth.json has been created successfully."
            logging.info(message)
            return jsonify({"message": message}), 200
        else:
            message = "Failed to create oauth.json."
            logging.error(message)
            return jsonify({"message": message}), 500

    except Exception as e:
        logging.error(f"An error occurred during the OAuth flow: {e}")
        return jsonify({"error": str(e)}), 500


def start_oauth_process() -> Popen:
    """
    Start the YouTube Music API OAuth process by executing the ytmusicapi oauth command.

    Returns:
        Popen: The subprocess instance for the OAuth process.
    """
    process: Popen = Popen(["ytmusicapi", "oauth"], stdout=PIPE, stderr=PIPE, stdin=PIPE)
    return process


def wait_for_user_interaction() -> None:
    """
    Wait for the user to interact with the Google OAuth page and press the required button.
    """
    logging.info("Waiting for 20 seconds to allow user to interact with the OAuth flow.")
    time.sleep(20)


def send_enter_key_to_process(process: Popen) -> None:
    """
    Send an Enter key input to the process to proceed with the OAuth flow.

    Args:
        process (Popen): The process to which the Enter key input should be sent.
    """
    logging.info("Sending Enter key input to the process.")
    process.communicate(input=b'\n')


if __name__ == '__main__':
    logging.info(f"Starting Flask server on port {PORT}.")
    app.run(port=PORT)
