import hashlib
import secrets


def hash_webhook_secret(secret: str) -> str:
    """Hash un secret webhook avec SHA-256 + salt."""
    # Générer un salt aléatoire
    salt = secrets.token_hex(16)
    # Hash SHA-256 avec salt
    hash_obj = hashlib.sha256((salt + secret).encode())
    return f"{salt}${hash_obj.hexdigest()}"


def verify_webhook_secret(secret: str, hashed: str) -> bool:
    """Vérifie un secret webhook contre son hash."""
    try:
        salt, hash_value = hashed.split('$')
        hash_obj = hashlib.sha256((salt + secret).encode())
        return hash_obj.hexdigest() == hash_value
    except:
        return False
