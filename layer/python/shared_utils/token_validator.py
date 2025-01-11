from datetime import datetime
import logging
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)

def is_token_valid(
    db_service: Any,
    user_id: str,
    service_prefix: str,
    refresh_callback: Callable[[str, str], Optional[str]]
) -> Optional[str]:
    """
    Check if service token is valid and refresh if needed.

    Args:
        db_service: Database service to retrieve tokens
        user_id: ID of the user to check tokens for
        service_prefix: Prefix used to identify the service tokens
        refresh_callback: Callback function to refresh expired tokens

    Returns:
        str: Valid access token if found/refreshed successfully
        None: If no valid token could be retrieved or refreshed
    """
    try:
        tokens: Dict[str, str] = db_service.get_tokens(user_id, service_prefix)
        if not tokens:
            logger.info(f"No tokens found for user {user_id}")
            return None

        current_time = int(datetime.now().timestamp())
        token_key = f"{service_prefix}_access_token"
        expires_key = f"{service_prefix}_expires_at"
        refresh_key = f"{service_prefix}_refresh_token"

        if token_key in tokens and expires_key in tokens:
            try:
                expires_at = int(tokens[expires_key])
                if expires_at > current_time:
                    logger.info(f"Valid token found for user {user_id}")
                    return tokens[token_key]
                logger.info(f"Token expired for user {user_id}")
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting expires_at to int: {str(e)}")
                return None

        if refresh_key in tokens:
            logger.info(f"Attempting to refresh token for user {user_id}")
            return refresh_callback(user_id, tokens[refresh_key])

        logger.info(f"No refresh token found for user {user_id}")
        return None

    except Exception as e:
        logger.error(f"Error validating token for user {user_id}: {str(e)}")
        return None