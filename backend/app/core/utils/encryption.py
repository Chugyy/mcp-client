# app/core/utils/encryption.py
"""Module de chiffrement/déchiffrement des clés API."""

from cryptography.fernet import Fernet
from config.config import settings
from config.logger import logger


def _get_fernet() -> Fernet:
    """Retourne une instance Fernet avec la clé maître."""
    try:
        return Fernet(settings.encryption_master_key.encode())
    except Exception as e:
        logger.error(f"Failed to initialize Fernet: {e}")
        raise ValueError("Invalid encryption master key. Check ENCRYPTION_MASTER_KEY in .env")


def encrypt_api_key(plain_value: str) -> str:
    """
    Chiffre une clé API en texte clair.

    Args:
        plain_value: La clé API en clair

    Returns:
        str: La clé chiffrée (base64)

    Raises:
        ValueError: Si le chiffrement échoue
    """
    try:
        fernet = _get_fernet()
        encrypted = fernet.encrypt(plain_value.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Failed to encrypt API key: {e}")
        raise ValueError(f"Encryption failed: {e}")


def decrypt_api_key(encrypted_value: str) -> str:
    """
    Déchiffre une clé API chiffrée.

    Args:
        encrypted_value: La clé chiffrée (base64)

    Returns:
        str: La clé en clair

    Raises:
        ValueError: Si le déchiffrement échoue
    """
    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        raise ValueError(f"Decryption failed: {e}")
