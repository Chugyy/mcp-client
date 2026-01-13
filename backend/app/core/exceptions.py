#!/usr/bin/env python3
# app/core/exceptions.py
"""
Exceptions métier typées pour l'application.

Utilisées dans toute l'application pour une gestion d'erreurs cohérente.
Chaque exception est mappée à un code HTTP spécifique via le handler global.
"""

from typing import Optional, Dict, Any


class AppException(Exception):
    """Exception de base pour toutes les exceptions métier."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Erreur de validation des données (HTTP 400)."""
    pass


class ConflictError(AppException):
    """Conflit avec l'état actuel (doublon, etc.) (HTTP 409)."""
    pass


class QuotaExceededError(AppException):
    """Quota dépassé (HTTP 429)."""
    pass


class PermissionError(AppException):
    """Permission refusée (HTTP 403)."""
    pass


class NotFoundError(AppException):
    """Ressource non trouvée (HTTP 404)."""
    pass


class AuthenticationError(AppException):
    """Erreur d'authentification (HTTP 401)."""
    pass


class RateLimitError(AppException):
    """Rate limit dépassé (HTTP 429)."""
    pass


class CircuitBreakerOpenError(AppException):
    """Circuit breaker is open, provider temporarily unavailable (HTTP 503)."""
    pass
