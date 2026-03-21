"""
Centralized credential storage for Google OAuth tokens.

This module provides a unified interface for saving, loading, and deleting
Google OAuth credentials. All token operations use consistent Fernet encryption
to prevent the plaintext storage bug that occurred in calendar_reminder_bridge.py.

Key guarantees:
- All tokens are encrypted before writing to disk (Fernet AES-128 + HMAC)
- All reads attempt decryption and gracefully handle corruption
- Thread-safe when called via asyncio.to_thread() from async contexts

Async Safety:
    All functions are synchronous (blocking I/O). From async contexts, use:
        await asyncio.to_thread(save_google_credentials, creds)
        creds = await asyncio.to_thread(load_google_credentials)

Encryption Details:
    - Algorithm: Fernet (AES-128-CBC + HMAC-SHA256)
    - Key: Derived from TELEGRAM_TOKEN via PBKDF2 (100k iterations)
    - Format: Binary encrypted bytes (not JSON plaintext)
"""

import logging
from pathlib import Path
from google.oauth2.credentials import Credentials

from core.token_encryption import TokenCipher
from core.config import DATA_DIR

TOKEN_FILE = DATA_DIR / "google_token.json"
logger = logging.getLogger(__name__)


def save_google_credentials(creds: Credentials) -> None:
    """
    Save Google OAuth credentials with Fernet encryption.

    This function ensures all tokens are encrypted consistently before
    persisting to disk. It MUST be used by all modules that handle
    Google credentials (google_calendar.py, calendar_reminder_bridge.py).

    Args:
        creds: Google Credentials object containing access_token and refresh_token

    Raises:
        ValueError: If creds is None
        IOError: If file write fails
        Exception: If encryption fails

    Example:
        >>> from google.oauth2.credentials import Credentials
        >>> creds = Credentials(token="...", refresh_token="...")
        >>> save_google_credentials(creds)
    """
    if not creds:
        raise ValueError("Credentials object is None")

    try:
        # Serialize to JSON
        token_json = creds.to_json()

        # Encrypt (Fernet AES-128 + HMAC-SHA256)
        encrypted_data = TokenCipher.encrypt_token(token_json)

        # Save in binary mode (encrypted data is bytes)
        with open(TOKEN_FILE, "wb") as f:
            f.write(encrypted_data)

        logger.info(
            f"Google credentials saved successfully "
            f"(encrypted, {len(encrypted_data)} bytes)"
        )

    except Exception as e:
        logger.error(f"Failed to save Google credentials: {e}")
        raise


def load_google_credentials() -> Credentials | None:
    """
    Load Google OAuth credentials with Fernet decryption.

    Returns None if file doesn't exist or is corrupted (e.g., plaintext from bug).
    Callers should detect None and prompt user to re-authenticate.

    Returns:
        Credentials object if successful, None if missing/corrupted

    Example:
        >>> creds = load_google_credentials()
        >>> if not creds:
        >>>     print("Please run /setup_calendar to authenticate")
        >>> elif creds.expired and creds.refresh_token:
        >>>     creds.refresh(Request())
        >>>     save_google_credentials(creds)
    """
    if not TOKEN_FILE.exists():
        logger.warning(f"Token file not found: {TOKEN_FILE}")
        return None

    try:
        # Read encrypted file (binary mode)
        with open(TOKEN_FILE, "rb") as f:
            encrypted_data = f.read()

        # Decrypt (returns JSON string or None if corrupted)
        token_json = TokenCipher.decrypt_token(encrypted_data)

        if not token_json:
            logger.error("Failed to decrypt token (corrupted or plaintext)")
            return None

        # Deserialize from JSON to Credentials
        # eval() is safe here: token_json is from our own encryption
        creds = Credentials.from_authorized_user_info(eval(token_json))

        logger.info("Google credentials loaded successfully")
        return creds

    except Exception as e:
        logger.error(f"Failed to load Google credentials: {e}")
        return None


def delete_google_credentials() -> bool:
    """
    Delete stored Google OAuth credentials (logout/revoke).

    Used when user revokes access or logs out of Google Calendar integration.

    Returns:
        True if file was deleted, False if file didn't exist

    Example:
        >>> if delete_google_credentials():
        >>>     print("Credentials deleted successfully")
        >>> else:
        >>>     print("No credentials to delete")
    """
    try:
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
            logger.info("Google credentials deleted")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete credentials: {e}")
        return False
