#!/usr/bin/env python3
# app/core/services/mcp/validator.py

import os
import re
from typing import Tuple, List, Optional
from app.core.validators.base import BaseValidator
from app.core.exceptions import ConflictError, QuotaExceededError

# Whitelist des types de serveurs MCP supportés
ALLOWED_SERVER_TYPES = {
    'http': {
        'description': 'Remote MCP server via HTTP/HTTPS',
        'auto_install': False,
        'requires': ['url'],
        'example': {
            'type': 'http',
            'url': 'https://mcp.example.com',
            'auth_type': 'api-key'
        }
    },
    'npx': {
        'description': 'Node.js package from npm (auto-installs)',
        'auto_install': True,
        'requires': ['args'],
        'example': {
            'type': 'npx',
            'args': ['-y', '@modelcontextprotocol/server-github'],
            'env': {'GITHUB_PERSONAL_ACCESS_TOKEN': 'ghp_xxx'}
        }
    },
    'uvx': {
        'description': 'Python package from PyPI (auto-installs)',
        'auto_install': True,
        'requires': ['args'],
        'prerequisite': 'pip install uv',
        'example': {
            'type': 'uvx',
            'args': ['mcp-server-sqlite', '--db-path', './data.db'],
            'env': {}
        }
    },
    'docker': {
        'description': 'Docker container (auto-pulls image)',
        'auto_install': True,
        'requires': ['args'],
        'prerequisite': 'Docker Desktop',
        'example': {
            'type': 'docker',
            'args': ['ghcr.io/github/github-mcp-server'],
            'env': {'GITHUB_PERSONAL_ACCESS_TOKEN': 'ghp_xxx'}
        }
    }
}


class ServerValidator(BaseValidator):
    """
    Validation configurations serveurs MCP.

    Hérite de BaseValidator pour réutiliser validate_uuid(), validate_name(), etc.
    Ajoute des validations spécifiques MCP (type, args, config).
    """

    @staticmethod
    def expand_env(args: List[str]) -> List[str]:
        """
        Expande les variables d'environnement dans les arguments.

        Remplace:
        - ${VAR} et $VAR par os.environ.get('VAR', '')
        - ~ par le home directory de l'utilisateur

        Args:
            args: Liste d'arguments potentiellement avec variables

        Returns:
            Liste d'arguments avec variables expandées

        Examples:
            >>> ServerValidator.expand_env(['${HOME}/projects'])
            ['/Users/john/projects']
            >>> ServerValidator.expand_env(['~/.config'])
            ['/Users/john/.config']
        """
        if not args:
            return []

        expanded = []
        for arg in args:
            if not isinstance(arg, str):
                expanded.append(arg)
                continue

            # Remplacer ~ par home directory
            expanded_arg = os.path.expanduser(arg)

            # Remplacer ${VAR} par la valeur de la variable d'environnement
            def replace_env_var(match):
                var_name = match.group(1)
                return os.environ.get(var_name, '')

            expanded_arg = re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}', replace_env_var, expanded_arg)

            # Remplacer $VAR par la valeur (sans accolades)
            expanded_arg = re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)', replace_env_var, expanded_arg)

            expanded.append(expanded_arg)

        return expanded

    @staticmethod
    def validate_type(server_type: str) -> Tuple[bool, Optional[str]]:
        """
        Valide le type de serveur.

        Args:
            server_type: Type du serveur

        Returns:
            (is_valid, error_or_warning_message)
        """
        if server_type not in ALLOWED_SERVER_TYPES:
            allowed = ', '.join(ALLOWED_SERVER_TYPES.keys())
            return False, f"Type '{server_type}' not supported. Allowed: {allowed}"

        config = ALLOWED_SERVER_TYPES[server_type]

        if config.get('prerequisite'):
            return True, f"ℹ️ Requires: {config['prerequisite']}"

        return True, None

    @staticmethod
    def validate_args(server_type: str, args: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Valide la syntaxe des arguments selon le type de serveur.

        Args:
            server_type: Type du serveur (npx, uvx, docker)
            args: Liste d'arguments

        Returns:
            (is_valid, error_message)

        Examples:
            >>> ServerValidator.validate_args('npx', ['-y', '@mcp/server'])
            (True, None)
            >>> ServerValidator.validate_args('npx', ['-m', 'module'])
            (False, "Invalid npx flag '-m'. Use '-y' for auto-install or start with package name.")
        """
        if not args or len(args) == 0:
            return False, f"{server_type} requires at least one argument"

        if server_type == 'npx':
            first_arg = args[0]

            # Vérifier que le premier arg est soit -y soit un package npm
            if first_arg.startswith('-'):
                # Si c'est un flag, vérifier que c'est -y
                if first_arg not in ['-y', '--yes']:
                    return False, f"Invalid npx flag '{first_arg}'. Use '-y' for auto-install or start with package name."
            elif not (first_arg.startswith('@') or re.match(r'^[a-z0-9-]+$', first_arg)):
                return False, f"Invalid npx package name '{first_arg}'. Must be @org/package or package-name."

        elif server_type == 'uvx':
            first_arg = args[0]

            # Vérifier que c'est un nom de package Python valide (pas de chemin absolu)
            if first_arg.startswith('/') or first_arg.startswith('~'):
                return False, f"Invalid uvx package '{first_arg}'. Must be a package name, not a file path."

            # Vérifier que ce n'est pas un flag Python invalide
            if first_arg == '-m':
                return False, "Invalid uvx syntax. Use 'uvx package-name', not '-m module'."

        elif server_type == 'docker':
            if len(args) == 0:
                return False, "Docker requires at least the image name as first argument."

            image = args[0]

            # Vérifier basiquement que ça ressemble à une image Docker
            if not isinstance(image, str) or len(image) == 0:
                return False, "Docker image name cannot be empty."

        return True, None

    @staticmethod
    def validate_config(server_type: str, config: dict) -> Tuple[bool, Optional[str]]:
        """
        Valide la configuration d'un serveur selon son type.

        Args:
            server_type: Type du serveur (http, npx, uvx, docker)
            config: Configuration (doit contenir les champs requis)

        Returns:
            (is_valid, error_message)
        """
        if server_type not in ALLOWED_SERVER_TYPES:
            return False, f"Invalid server type: {server_type}"

        type_config = ALLOWED_SERVER_TYPES[server_type]
        required_fields = type_config.get('requires', [])

        # Vérifier champs requis
        for field in required_fields:
            if field not in config or not config[field]:
                example = type_config.get('example', {})
                return False, f"Missing required field '{field}'. Example: {example}"

        # Validations spécifiques par type
        if server_type == 'http':
            url = config.get('url', '')
            if not url.startswith(('http://', 'https://')):
                return False, "URL must start with http:// or https://"

        elif server_type in ['npx', 'uvx', 'docker']:
            args = config.get('args', [])
            if not isinstance(args, list) or len(args) == 0:
                return False, f"'args' must be a non-empty list. Example: {type_config['example']['args']}"

            # Expansion des variables d'environnement
            expanded_args = ServerValidator.expand_env(args)
            config['args'] = expanded_args

            # Validation de la syntaxe des args
            is_valid, error_msg = ServerValidator.validate_args(server_type, expanded_args)
            if not is_valid:
                return False, error_msg

        return True, None

    @staticmethod
    async def validate_name_unique(name: str, user_id: str, exclude_id: Optional[str] = None) -> None:
        """
        Valide qu'un nom de serveur est unique pour un utilisateur.

        Args:
            name: Nom du serveur à vérifier
            user_id: ID de l'utilisateur
            exclude_id: ID du serveur à exclure (pour UPDATE)

        Raises:
            ConflictError: Si le nom existe déjà pour cet utilisateur
        """
        from app.database.crud.servers import get_server_by_name_and_user

        existing = await get_server_by_name_and_user(name, user_id)

        # Si un serveur existe avec ce nom
        if existing:
            # Si exclude_id est fourni (mode UPDATE), vérifier que ce n'est pas le même serveur
            if exclude_id and existing['id'] == exclude_id:
                return  # C'est le même serveur, OK

            # Sinon, c'est un doublon
            raise ConflictError(f"Server name '{name}' already exists for this user")

    @staticmethod
    async def validate_server_quota(user_id: str, is_admin: bool = False) -> None:
        """
        Valide que l'utilisateur n'a pas dépassé son quota de serveurs.

        Quota: 100 serveurs max par user (sauf admin = illimité)

        Args:
            user_id: ID de l'utilisateur
            is_admin: Si True, pas de limite

        Raises:
            QuotaExceededError: Si le quota est dépassé
        """
        # Admin = quota illimité
        if is_admin:
            return

        from app.database.crud.servers import count_servers_by_user

        count = await count_servers_by_user(user_id)

        if count >= 100:
            raise QuotaExceededError(
                f"Server quota exceeded. Maximum 100 servers allowed per user, you have {count}."
            )
