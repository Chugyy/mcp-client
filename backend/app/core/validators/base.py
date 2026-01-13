#!/usr/bin/env python3
# app/core/validators/base.py
"""
Validateurs de base réutilisables pour toute l'application.

Pattern: Tous les validateurs retournent (bool, Optional[str])
- (True, None) → Validation OK
- (False, "message d'erreur") → Validation KO
"""

import re
from typing import Tuple, Optional, List


class BaseValidator:
    """Classe de base pour tous les validateurs."""

    @staticmethod
    def validate_uuid(value: str, prefix: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Valide un UUID avec format {prefix}_{random}.

        Args:
            value: UUID à valider
            prefix: Préfixe attendu (ex: 'agent', 'server')

        Returns:
            (is_valid, error_message)

        Examples:
            >>> BaseValidator.validate_uuid("agent_abc123def456")
            (True, None)
            >>> BaseValidator.validate_uuid("invalid-id")
            (False, "Invalid UUID format")
        """
        if not value or not isinstance(value, str):
            return False, "UUID cannot be empty"

        # Pattern: prefix_alphanumeric
        pattern = r'^[a-z]+_[a-zA-Z0-9]+$'
        if not re.match(pattern, value):
            return False, "Invalid UUID format. Expected format: prefix_randomstring"

        # Vérifier prefix si spécifié
        if prefix:
            if not value.startswith(f"{prefix}_"):
                return False, f"UUID must start with '{prefix}_'"

        return True, None

    @staticmethod
    def validate_name(
        value: str,
        max_length: int = 100,
        pattern: str = r'^[a-zA-Z0-9\s\-_\.]+$'
    ) -> Tuple[bool, Optional[str]]:
        """
        Valide un nom (serveur, agent, etc.).

        Args:
            value: Nom à valider
            max_length: Longueur maximale (défaut 100)
            pattern: Pattern regex (défaut: alphanumeric + espaces + - _ .)

        Returns:
            (is_valid, error_message)

        Examples:
            >>> BaseValidator.validate_name("GitHub MCP")
            (True, None)
            >>> BaseValidator.validate_name("<script>")
            (False, "Invalid characters in name")
        """
        if not value or not isinstance(value, str):
            return False, "Name cannot be empty"

        value = value.strip()

        if len(value) == 0:
            return False, "Name cannot be empty after trimming"

        if len(value) > max_length:
            return False, f"Name too long (max {max_length} characters)"

        if not re.match(pattern, value):
            return False, f"Invalid characters in name. Allowed: letters, numbers, spaces, - _ ."

        return True, None

    @staticmethod
    def validate_url(value: str, max_length: int = 2048, require_https: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Valide une URL.

        Args:
            value: URL à valider
            max_length: Longueur maximale (défaut 2048)
            require_https: Si True, force HTTPS uniquement

        Returns:
            (is_valid, error_message)

        Examples:
            >>> BaseValidator.validate_url("https://example.com")
            (True, None)
            >>> BaseValidator.validate_url("ftp://example.com")
            (False, "URL must start with http:// or https://")
        """
        if not value or not isinstance(value, str):
            return False, "URL cannot be empty"

        if len(value) > max_length:
            return False, f"URL too long (max {max_length} characters)"

        if require_https:
            if not value.startswith('https://'):
                return False, "URL must start with https://"
        else:
            if not value.startswith(('http://', 'https://')):
                return False, "URL must start with http:// or https://"

        # Validation basique de format
        url_pattern = r'^https?://[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*'
        if not re.match(url_pattern, value):
            return False, "Invalid URL format"

        return True, None

    @staticmethod
    def validate_enum(value: str, allowed: List[str], case_sensitive: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Valide qu'une valeur fait partie d'une liste autorisée.

        Args:
            value: Valeur à valider
            allowed: Liste des valeurs autorisées
            case_sensitive: Si False, ignore la casse

        Returns:
            (is_valid, error_message)

        Examples:
            >>> BaseValidator.validate_enum("http", ["http", "npx"])
            (True, None)
            >>> BaseValidator.validate_enum("ftp", ["http", "npx"])
            (False, "Value 'ftp' not allowed. Allowed: http, npx")
        """
        if not value:
            return False, "Value cannot be empty"

        check_value = value if case_sensitive else value.lower()
        check_allowed = allowed if case_sensitive else [v.lower() for v in allowed]

        if check_value not in check_allowed:
            allowed_str = ', '.join(allowed)
            return False, f"Value '{value}' not allowed. Allowed: {allowed_str}"

        return True, None

    @staticmethod
    def validate_description(value: Optional[str], max_length: int = 500) -> Tuple[bool, Optional[str]]:
        """
        Valide une description (optionnelle).

        Args:
            value: Description à valider (peut être None)
            max_length: Longueur maximale

        Returns:
            (is_valid, error_message)
        """
        if value is None or value == "":
            return True, None

        if not isinstance(value, str):
            return False, "Description must be a string"

        if len(value) > max_length:
            return False, f"Description too long (max {max_length} characters)"

        return True, None
