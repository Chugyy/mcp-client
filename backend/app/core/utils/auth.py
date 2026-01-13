# auth.py

from datetime import datetime, timedelta
from typing import Optional, Union
import secrets
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config.config import settings
from config.logger import logger
from app.database.crud import get_user, get_user_by_email, create_user
from app.database.models import User
from app.core.exceptions import AuthenticationError

# Configuration du hachage de mot de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuration JWT (conservé pour compatibilité mais non utilisé en production)
security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hache un mot de passe."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crée un access token JWT (courte durée)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Access token courte durée : 15 minutes
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def generate_refresh_token() -> str:
    """Génère un refresh token aléatoire sécurisé."""
    return secrets.token_urlsafe(64)

def hash_refresh_token(token: str) -> str:
    """Hash un refresh token avec SHA256."""
    return hashlib.sha256(token.encode()).hexdigest()

async def create_refresh_token(user_id: str) -> tuple[str, str]:
    """
    Crée un refresh token et son hash.
    Returns: (token, token_hash)
    """
    from app.database.crud.refresh_tokens import create_refresh_token as db_create_refresh_token

    # Générer token aléatoire
    token = generate_refresh_token()
    token_hash = hash_refresh_token(token)

    # Stocker en DB avec expiration 7 jours
    expires_at = datetime.utcnow() + timedelta(days=7)
    await db_create_refresh_token(user_id, token_hash, expires_at)

    return token, token_hash

async def verify_refresh_token(token: str) -> Optional[str]:
    """
    Vérifie un refresh token et retourne l'user_id s'il est valide.
    Returns: user_id ou None
    """
    from app.database.crud.refresh_tokens import get_refresh_token_by_hash, revoke_refresh_token

    token_hash = hash_refresh_token(token)
    refresh_token_data = await get_refresh_token_by_hash(token_hash)

    if not refresh_token_data:
        logger.warning("Refresh token not found in database")
        return None

    # Vérifier si révoqué
    if refresh_token_data.get('revoked'):
        logger.warning("Refresh token is revoked")
        return None

    # Vérifier expiration
    expires_at = refresh_token_data.get('expires_at')
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)

    if expires_at < datetime.utcnow():
        logger.warning("Refresh token expired")
        await revoke_refresh_token(token_hash)
        return None

    return refresh_token_data.get('user_id')

def verify_token(token: str) -> Optional[str]:
    """Vérifie un token JWT et retourne l'user_id."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None

async def authenticate_user(email: str, password: str) -> Union[User, bool]:
    """Authentifie un utilisateur par email."""
    user_dict = await get_user_by_email(email)

    if not user_dict:
        return False

    user = User.from_row(user_dict)

    if not verify_password(password, user.password):
        return False

    return user

async def get_current_user(request: Request) -> User:
    """Récupère l'utilisateur actuel depuis le cookie access_token."""
    logger.debug("get_current_user() called")

    # Lire le cookie access_token
    token = request.cookies.get("access_token")

    if not token:
        logger.warning("No access_token cookie found")
        raise AuthenticationError("Not authenticated")

    # Vérifier le token JWT
    user_id = verify_token(token)
    logger.debug(f"Token verified, user_id={user_id}")

    if user_id is None:
        logger.warning("Invalid token, user_id is None")
        raise AuthenticationError("Invalid or expired token")

    # Récupérer l'utilisateur
    user_dict = await get_user(user_id)
    if user_dict is None:
        logger.warning(f"User not found for user_id={user_id}")
        raise AuthenticationError("User not found")

    return User.from_row(user_dict)