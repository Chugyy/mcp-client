from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from app.database.crud import uploads, servers as crud_servers, resources as crud_resources

@dataclass
class User:
    id: str
    email: str
    password: str
    name: str
    preferences: dict
    created_at: datetime
    updated_at: datetime
    permission_level: str = 'validation_required'  # full_auto, validation_required, no_tools
    is_system: bool = False  # Super-admin flag

    @classmethod
    def from_row(cls, row) -> "User":
        # Parser preferences si c'est une string JSON
        preferences = row['preferences']
        if isinstance(preferences, str):
            preferences = json.loads(preferences) if preferences else {}
        elif preferences is None:
            preferences = {}

        return cls(
            id=row['id'],
            email=row['email'],
            password=row['password'],
            name=row['name'],
            preferences=preferences,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            permission_level=row.get('permission_level', 'validation_required'),
            is_system=row.get('is_system', False)
        )

    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "preferences": self.preferences,
            "permission_level": self.permission_level,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }
        if include_password:
            data["password"] = self.password
        return data

@dataclass
class ResetToken:
    id: str
    user_id: str
    token: str
    expires_at: datetime
    used: bool
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "ResetToken":
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            token=row['token'],
            expires_at=row['expires_at'],
            used=row['used'],
            created_at=row['created_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "token": self.token,
            "expires_at": self.expires_at.isoformat() if isinstance(self.expires_at, datetime) else self.expires_at,
            "used": self.used,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }

@dataclass
class Agent:
    id: str
    user_id: str
    name: str
    description: Optional[str]
    system_prompt: str
    tags: List[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    is_system: bool = False

    @classmethod
    def from_row(cls, row) -> "Agent":
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            name=row['name'],
            description=row['description'],
            system_prompt=row['system_prompt'],
            tags=row['tags'] if row['tags'] else [],
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            is_system=row.get('is_system', False)
        )

    async def to_dict(self) -> Dict[str, Any]:
        avatar_url = await uploads.get_agent_avatar_url(self.id)

        # Retrieve MCP configurations
        server_configs = await crud_servers.list_configurations_by_agent(self.id, 'server')

        # Build mcp_configs structure from stored configurations with server details
        mcp_configs = []
        for config in server_configs:
            server_id = config['entity_id']
            config_data = config.get('config_data', {})

            # Parse config_data if it's a JSON string
            if isinstance(config_data, str):
                config_data = json.loads(config_data) if config_data else {}

            # Get tools list from config_data
            tools = config_data.get('tools', []) if isinstance(config_data, dict) else []

            # Fetch server details
            server = await crud_servers.get_server(server_id)

            # Fetch tools details for this server
            server_tools = await crud_servers.list_tools_by_server(server_id) if server else []

            # Enrich tools with their full information
            enriched_tools = []
            for tool_config in tools:
                tool_id = tool_config.get('id')
                tool_enabled = tool_config.get('enabled', True)

                # Find matching tool detail
                tool_detail = next((t for t in server_tools if t['id'] == tool_id), None)

                enriched_tools.append({
                    'id': tool_id,
                    'name': tool_detail['name'] if tool_detail else None,
                    'description': tool_detail['description'] if tool_detail else None,
                    'enabled': tool_enabled
                })

            mcp_configs.append({
                'id': config['id'],
                'server_id': server_id,
                'server_name': server['name'] if server else None,
                'server_url': server['url'] if server else None,
                'enabled': config['enabled'],
                'tools': enriched_tools
            })

        # Retrieve resource configurations with resource details
        resource_configs = await crud_servers.list_configurations_by_agent(self.id, 'resource')
        resources = []
        for config in resource_configs:
            resource_id = config['entity_id']

            # Fetch resource details
            resource = await crud_resources.get_resource(resource_id)

            # Get uploads for this resource
            resource_uploads = await uploads.list_uploads_by_resource(resource_id) if resource else []

            resources.append({
                'id': resource_id,
                'name': resource['name'] if resource else None,
                'description': resource.get('description') if resource else None,
                'status': resource.get('status') if resource else None,
                'enabled': config['enabled'],
                'uploads': [
                    {
                        'id': u['id'],
                        'filename': u['filename'],
                        'file_size': u['file_size'],
                        'mime_type': u['mime_type']
                    }
                    for u in resource_uploads
                ]
            })

        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "tags": self.tags,
            "enabled": self.enabled,
            "is_system": self.is_system,
            "avatar_url": avatar_url,
            "mcp_configs": mcp_configs,
            "resources": resources,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }

@dataclass
class Upload:
    id: str
    user_id: Optional[str]
    agent_id: Optional[str]
    resource_id: Optional[str]
    type: str
    filename: str
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "Upload":
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            agent_id=row['agent_id'],
            resource_id=row.get('resource_id'),
            type=row['type'],
            filename=row['filename'],
            file_path=row['file_path'],
            file_size=row['file_size'],
            mime_type=row['mime_type'],
            created_at=row['created_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "resource_id": self.resource_id,
            "type": self.type,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }

@dataclass
class Team:
    id: str
    name: str
    description: Optional[str]
    system_prompt: str
    tags: List[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row) -> "Team":
        return cls(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            system_prompt=row['system_prompt'],
            tags=row['tags'] if row['tags'] else [],
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "tags": self.tags,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }

@dataclass
class Membership:
    id: str
    team_id: str
    agent_id: str
    enabled: bool
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "Membership":
        return cls(
            id=row['id'],
            team_id=row['team_id'],
            agent_id=row['agent_id'],
            enabled=row['enabled'],
            created_at=row['created_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "agent_id": self.agent_id,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }

@dataclass
class Chat:
    id: str
    user_id: str
    agent_id: Optional[str]
    team_id: Optional[str]
    title: str
    created_at: datetime
    updated_at: datetime
    model: Optional[str] = None
    initialized_at: Optional[datetime] = None
    awaiting_validation_id: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Chat":
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            agent_id=row['agent_id'],
            team_id=row['team_id'],
            title=row['title'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            model=row.get('model'),
            initialized_at=row.get('initialized_at'),
            awaiting_validation_id=row.get('awaiting_validation_id')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "team_id": self.team_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "model": self.model,
            "initialized_at": self.initialized_at.isoformat() if isinstance(self.initialized_at, datetime) and self.initialized_at else None
        }

    def is_initialized(self) -> bool:
        """Returns True if the chat has been initialized."""
        return self.initialized_at is not None

    def is_empty(self) -> bool:
        """Returns True if the chat has not been initialized yet."""
        return self.initialized_at is None

@dataclass
class Message:
    id: str
    chat_id: str
    role: str
    content: str
    metadata: dict
    created_at: datetime
    turn_id: Optional[str] = None
    sequence_index: Optional[int] = None

    @classmethod
    def from_row(cls, row) -> "Message":
        # Parser metadata si c'est une string JSON
        metadata = row['metadata']
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        elif metadata is None:
            metadata = {}

        return cls(
            id=row['id'],
            chat_id=row['chat_id'],
            role=row['role'],
            content=row['content'],
            metadata=metadata,
            created_at=row['created_at'],
            turn_id=row.get('turn_id'),
            sequence_index=row.get('sequence_index')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "turn_id": self.turn_id,
            "sequence_index": self.sequence_index
        }

@dataclass
class Validation:
    id: str
    user_id: str
    agent_id: Optional[str]
    title: str
    description: Optional[str]
    source: str
    process: str
    status: str
    created_at: datetime
    updated_at: datetime
    # Nouveaux champs pour le système de validation des tool calls
    chat_id: Optional[str] = None
    tool_name: Optional[str] = None
    server_id: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_result: Optional[dict] = None
    expires_at: Optional[datetime] = None
    execution_id: Optional[str] = None
    expired_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row) -> "Validation":
        # Parser tool_args si c'est une string JSON
        tool_args = row.get('tool_args')
        if isinstance(tool_args, str):
            tool_args = json.loads(tool_args) if tool_args else None

        # Parser tool_result si c'est une string JSON
        tool_result = row.get('tool_result')
        if isinstance(tool_result, str):
            tool_result = json.loads(tool_result) if tool_result else None

        return cls(
            id=row['id'],
            user_id=row['user_id'],
            agent_id=row['agent_id'],
            title=row['title'],
            description=row['description'],
            source=row['source'],
            process=row['process'],
            status=row['status'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            chat_id=row.get('chat_id'),
            tool_name=row.get('tool_name'),
            server_id=row.get('server_id'),
            tool_args=tool_args,
            tool_result=tool_result,
            expires_at=row.get('expires_at'),
            execution_id=row.get('execution_id'),
            expired_at=row.get('expired_at')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "process": self.process,
            "status": self.status,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "chat_id": self.chat_id,
            "tool_name": self.tool_name,
            "server_id": self.server_id,
            "tool_args": self.tool_args,
            "tool_result": self.tool_result,
            "expires_at": self.expires_at.isoformat() if isinstance(self.expires_at, datetime) else self.expires_at
        }

@dataclass
class Resource:
    id: str
    name: str
    description: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    status: str = 'pending'
    chunk_count: int = 0
    embedding_model: str = 'text-embedding-3-large'
    embedding_dim: int = 3072
    indexed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    is_system: bool = False

    @classmethod
    def from_row(cls, row) -> "Resource":
        return cls(
            id=row['id'],
            name=row['name'],
            description=row.get('description'),
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            status=row.get('status', 'pending'),
            chunk_count=row.get('chunk_count', 0),
            embedding_model=row.get('embedding_model', 'text-embedding-3-large'),
            embedding_dim=row.get('embedding_dim', 3072),
            indexed_at=row.get('indexed_at'),
            error_message=row.get('error_message'),
            is_system=row.get('is_system', False)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "status": self.status,
            "chunk_count": self.chunk_count,
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "indexed_at": self.indexed_at.isoformat() if isinstance(self.indexed_at, datetime) and self.indexed_at else None,
            "error_message": self.error_message,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }

@dataclass
class Server:
    id: str
    name: str
    description: Optional[str]
    url: Optional[str]  # Maintenant nullable
    auth_type: Optional[str]
    service_id: Optional[str]
    api_key_id: Optional[str]
    enabled: bool
    status: str
    status_message: Optional[str]
    last_health_check: Optional[datetime]
    user_id: str
    is_system: bool
    is_public: bool
    created_at: datetime
    updated_at: datetime
    type: str = 'http'  # 🆕
    args: Optional[list] = None  # 🆕
    env: Optional[dict] = None  # 🆕

    @classmethod
    def from_row(cls, row) -> "Server":
        """Crée une instance depuis une row PostgreSQL."""
        import json

        # Parser args et env depuis JSONB
        args = row.get('args')
        if isinstance(args, str):
            args = json.loads(args)

        env = row.get('env')
        if isinstance(env, str):
            env = json.loads(env)

        return cls(
            id=row['id'],
            name=row['name'],
            description=row.get('description'),
            url=row.get('url'),
            auth_type=row.get('auth_type'),
            service_id=row.get('service_id'),
            api_key_id=row.get('api_key_id'),
            enabled=row['enabled'],
            status=row.get('status', 'pending'),
            status_message=row.get('status_message'),
            last_health_check=row.get('last_health_check'),
            user_id=row.get('user_id'),
            is_system=row.get('is_system', False),
            is_public=row.get('is_public', False),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            type=row.get('type', 'http'),  # 🆕
            args=args,  # 🆕
            env=env  # 🆕
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire (pour API response)."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'url': self.url,
            'auth_type': self.auth_type,
            'service_id': self.service_id,
            'api_key_id': self.api_key_id,
            'enabled': self.enabled,
            'status': self.status,
            'status_message': self.status_message,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'user_id': self.user_id,
            'is_system': self.is_system,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'type': self.type,  # 🆕
            'args': self.args,  # 🆕
            # 🔒 Ne PAS retourner env (contient secrets)
        }

@dataclass
class Tool:
    id: str
    server_id: str
    name: str
    description: Optional[str]
    enabled: bool
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "Tool":
        return cls(
            id=row['id'],
            server_id=row['server_id'],
            name=row['name'],
            description=row['description'],
            enabled=row['enabled'],
            created_at=row['created_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "server_id": self.server_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }

@dataclass
class Configuration:
    id: str
    agent_id: str
    entity_type: str
    entity_id: str
    config_data: dict
    enabled: bool
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "Configuration":
        # Parser config_data si c'est une string JSON
        config_data = row['config_data']
        if isinstance(config_data, str):
            config_data = json.loads(config_data) if config_data else {}
        elif config_data is None:
            config_data = {}

        return cls(
            id=row['id'],
            agent_id=row['agent_id'],
            entity_type=row['entity_type'],
            entity_id=row['entity_id'],
            config_data=config_data,
            enabled=row['enabled'],
            created_at=row['created_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "config_data": self.config_data,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }

@dataclass
class ApiKey:
    id: str
    encrypted_value: str
    user_id: str
    service_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row) -> "ApiKey":
        return cls(
            id=row['id'],
            encrypted_value=row['encrypted_value'],
            user_id=row['user_id'],
            service_id=row['service_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "encrypted_value": self.encrypted_value,
            "user_id": self.user_id,
            "service_id": self.service_id,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }

@dataclass
class Service:
    id: str
    name: str
    provider: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    logo_upload_id: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Service":
        return cls(
            id=row['id'],
            name=row['name'],
            provider=row['provider'],
            description=row['description'],
            status=row['status'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            logo_upload_id=row.get('logo_upload_id')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "logo_upload_id": self.logo_upload_id
        }

@dataclass
class Model:
    id: str
    service_id: str
    model_name: str
    display_name: Optional[str]
    description: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row) -> "Model":
        return cls(
            id=row['id'],
            service_id=row['service_id'],
            model_name=row['model_name'],
            display_name=row['display_name'],
            description=row['description'],
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "service_id": self.service_id,
            "model_name": self.model_name,
            "display_name": self.display_name,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }

@dataclass
class UserProvider:
    id: str
    user_id: str
    service_id: str
    api_key_id: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row) -> "UserProvider":
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            service_id=row['service_id'],
            api_key_id=row.get('api_key_id'),
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "service_id": self.service_id,
            "api_key_id": self.api_key_id,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }

@dataclass
class Log:
    id: str
    user_id: str
    agent_id: Optional[str]
    chat_id: Optional[str]
    type: str
    data: dict
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "Log":
        # Parser data si c'est une string JSON
        data = row['data']
        if isinstance(data, str):
            data = json.loads(data) if data else {}
        elif data is None:
            data = {}

        return cls(
            id=row['id'],
            user_id=row['user_id'],
            agent_id=row.get('agent_id'),
            chat_id=row.get('chat_id'),
            type=row['type'],
            data=data,
            created_at=row['created_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "chat_id": self.chat_id,
            "type": self.type,
            "data": self.data,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }

@dataclass
class Automation:
    id: str
    user_id: str
    name: str
    description: Optional[str]
    is_system: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row) -> "Automation":
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            name=row['name'],
            description=row['description'],
            is_system=row['is_system'],
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "is_system": self.is_system,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }

@dataclass
class WorkflowStep:
    id: str
    automation_id: str
    step_order: int
    step_name: str
    step_type: str
    step_subtype: str
    config: dict
    run_condition: Optional[str]
    enabled: bool
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "WorkflowStep":
        config = row['config']
        if isinstance(config, str):
            config = json.loads(config) if config else {}
        elif config is None:
            config = {}

        return cls(
            id=row['id'],
            automation_id=row['automation_id'],
            step_order=row['step_order'],
            step_name=row['step_name'],
            step_type=row['step_type'],
            step_subtype=row['step_subtype'],
            config=config,
            run_condition=row.get('run_condition'),
            enabled=row['enabled'],
            created_at=row['created_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "automation_id": self.automation_id,
            "step_order": self.step_order,
            "step_name": self.step_name,
            "step_type": self.step_type,
            "step_subtype": self.step_subtype,
            "config": self.config,
            "run_condition": self.run_condition,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }

@dataclass
class Trigger:
    id: str
    automation_id: str
    trigger_type: str
    config: dict
    enabled: bool
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "Trigger":
        config = row['config']
        if isinstance(config, str):
            config = json.loads(config) if config else {}
        elif config is None:
            config = {}

        return cls(
            id=row['id'],
            automation_id=row['automation_id'],
            trigger_type=row['trigger_type'],
            config=config,
            enabled=row['enabled'],
            created_at=row['created_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "automation_id": self.automation_id,
            "trigger_type": self.trigger_type,
            "config": self.config,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }

@dataclass
class Execution:
    id: str
    automation_id: str
    trigger_id: Optional[str]
    user_id: str
    status: str
    input_params: dict
    result: Optional[dict]
    error: Optional[str]
    error_step_id: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    paused_at: Optional[datetime] = None
    execution_state: Optional[dict] = None

    @classmethod
    def from_row(cls, row) -> "Execution":
        input_params = row['input_params']
        if isinstance(input_params, str):
            input_params = json.loads(input_params) if input_params else {}
        elif input_params is None:
            input_params = {}

        result = row.get('result')
        if isinstance(result, str):
            result = json.loads(result) if result else None

        execution_state = row.get('execution_state')
        if isinstance(execution_state, str):
            execution_state = json.loads(execution_state) if execution_state else None

        return cls(
            id=row['id'],
            automation_id=row['automation_id'],
            trigger_id=row.get('trigger_id'),
            user_id=row['user_id'],
            status=row['status'],
            input_params=input_params,
            result=result,
            error=row.get('error'),
            error_step_id=row.get('error_step_id'),
            started_at=row['started_at'],
            completed_at=row.get('completed_at'),
            paused_at=row.get('paused_at'),
            execution_state=execution_state
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "automation_id": self.automation_id,
            "trigger_id": self.trigger_id,
            "user_id": self.user_id,
            "status": self.status,
            "input_params": self.input_params,
            "result": self.result,
            "error": self.error,
            "error_step_id": self.error_step_id,
            "started_at": self.started_at.isoformat() if isinstance(self.started_at, datetime) else self.started_at,
            "completed_at": self.completed_at.isoformat() if isinstance(self.completed_at, datetime) and self.completed_at else None
        }

@dataclass
class ExecutionStepLog:
    id: str
    execution_id: str
    step_id: str
    status: str
    result: Optional[dict]
    error: Optional[str]
    duration_ms: Optional[int]
    executed_at: datetime

    @classmethod
    def from_row(cls, row) -> "ExecutionStepLog":
        result = row.get('result')
        if isinstance(result, str):
            result = json.loads(result) if result else None

        return cls(
            id=row['id'],
            execution_id=row['execution_id'],
            step_id=row['step_id'],
            status=row['status'],
            result=result,
            error=row.get('error'),
            duration_ms=row.get('duration_ms'),
            executed_at=row['executed_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "step_id": self.step_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "executed_at": self.executed_at.isoformat() if isinstance(self.executed_at, datetime) else self.executed_at
        }
