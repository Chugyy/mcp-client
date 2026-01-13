# app/database/crud/__init__.py
# Point d'entrée unique pour toutes les fonctions CRUD
# Maintient la compatibilité avec les imports existants

from .users import (
    create_user,
    get_user,
    get_user_by_email,
    list_users,
    update_user,
    update_user_password,
    delete_user,
    create_reset_token,
    get_reset_token,
    mark_token_used
)

from .agents import (
    create_agent,
    get_agent,
    list_agents_by_user,
    update_agent,
    delete_agent,
    duplicate_agent
)

from .teams import (
    create_team,
    get_team,
    list_teams,
    update_team,
    delete_team,
    add_member,
    get_membership,
    remove_member,
    list_team_members,
    get_agent_teams
)

from .chats import (
    create_chat,
    get_chat,
    list_chats_by_user,
    update_chat_title,
    delete_chat,
    set_validation_pending,
    initialize_chat,
    create_message,
    get_messages_by_chat,
    delete_message,
    get_message,
    update_message_content_and_metadata,
    update_message_turn_info,
    get_empty_chats_stats,
    delete_empty_chats_older_than
)

from .uploads import (
    create_upload,
    get_upload,
    list_uploads_by_user,
    list_uploads_by_agent,
    list_uploads_by_resource,
    delete_upload
)

from .resources import (
    create_resource,
    get_resource,
    list_resources,
    update_resource,
    update_resource_status,
    delete_resource
)

from .validations import (
    create_validation,
    get_validation,
    list_validations_by_user,
    get_validations_by_execution,
    update_validation_status,
    delete_validation,
    cancel_all_pending_validations
)

from .servers import (
    create_server,
    get_server,
    list_servers,
    list_servers_by_user,
    update_server,
    update_server_status,
    delete_server,
    create_tool,
    get_tool,
    list_tools_by_server,
    update_tool,
    delete_tool,
    delete_server_tools,
    create_configuration,
    list_configurations_by_agent,
    delete_configuration,
    toggle_configuration
)

from .api_keys import (
    create_api_key,
    get_api_key,
    get_api_key_decrypted,
    list_api_keys,
    update_api_key,
    delete_api_key
)

from .services import (
    create_service,
    get_service,
    list_services,
    update_service,
    delete_service,
    get_service_by_name_and_provider
)

from .models import (
    create_model,
    get_model,
    list_models,
    update_model,
    delete_model,
    get_model_by_name,
    list_models_with_service,
    list_models_for_user
)

from .user_providers import (
    create_user_provider,
    get_user_provider,
    get_user_provider_by_service,
    list_user_providers,
    update_user_provider,
    delete_user_provider
)

from .logs import (
    create_log,
    get_log,
    list_logs_by_chat,
    list_logs_by_user,
    check_tool_cache,
    get_tool_cache_entry,
    delete_tool_cache,
    count_tool_executions,
    get_logs_by_validation_id
)

from .automations import (
    create_automation,
    get_automation,
    list_automations,
    list_cron_automations,
    update_automation,
    delete_automation
)

from .workflow_steps import (
    create_workflow_step,
    get_workflow_step,
    get_workflow_steps
)

from .triggers import (
    create_trigger,
    get_trigger,
    get_triggers
)

from .executions import (
    create_execution,
    update_execution_status,
    update_execution,
    create_step_log,
    get_execution_step_logs,
    get_execution,
    list_executions
)

from .refresh_tokens import (
    create_refresh_token,
    get_refresh_token_by_hash,
    revoke_refresh_token,
    revoke_all_user_tokens,
    delete_expired_tokens,
    get_user_active_tokens,
    count_user_active_tokens
)

__all__ = [
    # Users
    'create_user',
    'get_user',
    'get_user_by_email',
    'list_users',
    'update_user',
    'update_user_password',
    'delete_user',

    # Reset Tokens
    'create_reset_token',
    'get_reset_token',
    'mark_token_used',

    # Agents
    'create_agent',
    'get_agent',
    'list_agents_by_user',
    'update_agent',
    'delete_agent',
    'duplicate_agent',

    # Teams
    'create_team',
    'get_team',
    'list_teams',
    'update_team',
    'delete_team',

    # Memberships
    'add_member',
    'get_membership',
    'remove_member',
    'list_team_members',
    'get_agent_teams',

    # Chats
    'create_chat',
    'get_chat',
    'list_chats_by_user',
    'update_chat_title',
    'delete_chat',
    'set_validation_pending',
    'initialize_chat',

    # Messages
    'create_message',
    'get_messages_by_chat',
    'delete_message',
    'get_message',
    'update_message_content_and_metadata',
    'update_message_turn_info',

    # Chat utilities
    'get_empty_chats_stats',
    'delete_empty_chats_older_than',

    # Uploads
    'create_upload',
    'get_upload',
    'list_uploads_by_user',
    'list_uploads_by_agent',
    'list_uploads_by_resource',
    'delete_upload',

    # Resources
    'create_resource',
    'get_resource',
    'list_resources',
    'update_resource',
    'update_resource_status',
    'delete_resource',

    # Validations
    'create_validation',
    'get_validation',
    'list_validations_by_user',
    'get_validations_by_execution',
    'update_validation_status',
    'delete_validation',
    'cancel_all_pending_validations',

    # Servers
    'create_server',
    'get_server',
    'list_servers',
    'list_servers_by_user',
    'update_server',
    'update_server_status',
    'delete_server',

    # Tools
    'create_tool',
    'get_tool',
    'list_tools_by_server',
    'update_tool',
    'delete_tool',
    'delete_server_tools',

    # Configurations
    'create_configuration',
    'list_configurations_by_agent',
    'delete_configuration',
    'toggle_configuration',

    # API Keys
    'create_api_key',
    'get_api_key',
    'get_api_key_decrypted',
    'list_api_keys',
    'update_api_key',
    'delete_api_key',

    # Services
    'create_service',
    'get_service',
    'list_services',
    'update_service',
    'delete_service',
    'get_service_by_name_and_provider',

    # Models
    'create_model',
    'get_model',
    'list_models',
    'update_model',
    'delete_model',
    'get_model_by_name',
    'list_models_with_service',
    'list_models_for_user',

    # User Providers
    'create_user_provider',
    'get_user_provider',
    'get_user_provider_by_service',
    'list_user_providers',
    'update_user_provider',
    'delete_user_provider',

    # Logs
    'create_log',
    'get_log',
    'list_logs_by_chat',
    'list_logs_by_user',
    'check_tool_cache',
    'get_tool_cache_entry',
    'delete_tool_cache',
    'count_tool_executions',
    'get_logs_by_validation_id',

    # Automations
    'create_automation',
    'get_automation',
    'list_automations',
    'list_cron_automations',
    'update_automation',
    'delete_automation',

    # Workflow Steps
    'create_workflow_step',
    'get_workflow_step',
    'get_workflow_steps',

    # Triggers
    'create_trigger',
    'get_trigger',
    'get_triggers',

    # Executions
    'create_execution',
    'update_execution_status',
    'update_execution',
    'create_step_log',
    'get_execution_step_logs',
    'get_execution',
    'list_executions',

    # Refresh Tokens
    'create_refresh_token',
    'get_refresh_token_by_hash',
    'revoke_refresh_token',
    'revoke_all_user_tokens',
    'delete_expired_tokens',
    'get_user_active_tokens',
    'count_user_active_tokens',
]
