#!/usr/bin/env python3
# app/api/routes/auth.py

from fastapi import APIRouter, Depends, status, Response, Request

from app.database import crud
from app.database.models import User
from app.core.utils.auth import (
    hash_password, authenticate_user, create_access_token, get_current_user,
    verify_refresh_token
)
from app.api.v1.schemas import UserRegister, UserLogin, Token
from app.core.exceptions import ValidationError, AuthenticationError
from config.logger import logger

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: UserRegister, response: Response):
    """Inscription d'un nouvel utilisateur."""
    # Vérifier si l'email existe déjà
    existing_user = await crud.get_user_by_email(request.email)
    if existing_user:
        raise ValidationError("Email already exists")

    # Créer l'utilisateur
    password_hash = hash_password(request.password)
    user_id = await crud.create_user(
        email=request.email,
        password=password_hash,
        name=request.name
    )

    # Créer access token (15 minutes)
    access_token = create_access_token(data={"sub": user_id})

    # Créer refresh token (7 jours)
    from app.core.utils.auth import create_refresh_token
    refresh_token, _ = await create_refresh_token(user_id)

    # Stocker access_token dans un cookie httpOnly (15 min)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # True en production (HTTPS)
        samesite="strict",
        max_age=15 * 60  # 15 minutes
    )

    # Stocker refresh_token dans un cookie httpOnly (7 jours)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # True en production (HTTPS)
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7 jours
        path="/api/v1/auth/refresh"  # Restreindre au endpoint refresh
    )

    return {"user_id": user_id, "email": request.email, "name": request.name}

@router.post("/login")
async def login(request: UserLogin, response: Response):
    """Connexion utilisateur avec email."""
    user = await authenticate_user(request.email, request.password)
    if not user:
        raise AuthenticationError("Incorrect email or password")

    # Créer access token (15 minutes)
    access_token = create_access_token(data={"sub": user.id})

    # Créer refresh token (7 jours)
    from app.core.utils.auth import create_refresh_token
    refresh_token, _ = await create_refresh_token(user.id)

    # Stocker access_token dans un cookie httpOnly (15 min)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # True en production (HTTPS)
        samesite="strict",
        max_age=15 * 60  # 15 minutes
    )

    # Stocker refresh_token dans un cookie httpOnly (7 jours)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # True en production (HTTPS)
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7 jours
        path="/api/v1/auth/refresh"  # Restreindre au endpoint refresh
    )

    return {"user_id": user.id, "email": user.email, "name": user.name}

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Récupère les informations de l'utilisateur connecté."""
    return current_user.to_dict()

@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """
    Rafraîchit l'access token en utilisant le refresh token.
    Le refresh token doit être présent dans les cookies.
    """
    # Récupérer le refresh token du cookie
    refresh_token_value = request.cookies.get("refresh_token")

    if not refresh_token_value:
        logger.warning("No refresh token in cookies")
        raise AuthenticationError("No refresh token provided")

    # Vérifier le refresh token et récupérer l'user_id
    user_id = await verify_refresh_token(refresh_token_value)

    if not user_id:
        logger.warning("Invalid or expired refresh token")
        raise AuthenticationError("Invalid or expired refresh token")

    # Créer un nouvel access token
    new_access_token = create_access_token(data={"sub": user_id})

    # Mettre à jour le cookie access_token
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=False,  # True en production (HTTPS)
        samesite="strict",
        max_age=15 * 60  # 15 minutes
    )

    logger.info(f"Access token refreshed for user {user_id}")
    return {"status": "refreshed"}

@router.post("/logout")
async def logout(request: Request, response: Response):
    """Déconnexion - révoque le refresh token et supprime les cookies."""
    from app.core.utils.auth import hash_refresh_token
    from app.database.crud.refresh_tokens import revoke_refresh_token

    # Récupérer le refresh token du cookie
    refresh_token = request.cookies.get("refresh_token")

    if refresh_token:
        # Révoquer le refresh token en DB
        token_hash = hash_refresh_token(refresh_token)
        await revoke_refresh_token(token_hash)

    # Supprimer les cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")

    return {"message": "Logged out successfully"}