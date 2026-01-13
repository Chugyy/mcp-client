// Types pour les serveurs MCP conformes à l'API Backend

export type MCPServerType = 'http' | 'npx' | 'uvx' | 'docker'

export interface MCPServer {
  id: string
  name: string
  description: string | null
  type: MCPServerType

  // HTTP fields
  url?: string
  auth_type?: 'api-key' | 'oauth' | 'none'
  api_key_id?: string | null

  // Stdio fields (npx, uvx, docker)
  args?: string[]
  // env is NEVER returned by API (security)

  enabled: boolean
  status: 'pending' | 'pending_authorization' | 'active' | 'failed' | 'unreachable'
  status_message: string | null
  last_health_check: string | null
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface MCPServerWithTools extends MCPServer {
  tools: MCPTool[]
  stale: boolean
}

export interface MCPTool {
  id: string
  server_id: string
  name: string
  description: string | null
  enabled: boolean
  created_at: string
}

export interface MCPConfiguration {
  id: string
  agent_id: string
  entity_type: 'server' | 'resource'
  entity_id: string
  config_data: object
  enabled: boolean
  created_at: string
}

// DTOs
export interface CreateMCPServerDTO {
  name: string
  description?: string | null
  type: MCPServerType

  // HTTP
  url?: string | null
  auth_type?: 'api-key' | 'oauth' | 'none' | null
  service_id?: string | null
  api_key_value?: string | null

  // Stdio (npx, uvx, docker)
  args?: string[] | null
  env?: Record<string, string> | null

  enabled?: boolean
}

export interface UpdateMCPServerDTO {
  name?: string | null
  description?: string | null
  url?: string | null
  auth_type?: 'api-key' | 'oauth' | 'none' | null
  service_id?: string | null
  enabled?: boolean | null
}

export interface CreateMCPToolDTO {
  name: string
  description?: string | null
  enabled?: boolean
}

export interface CreateMCPConfigurationDTO {
  entity_type: 'server' | 'resource'
  entity_id: string
  config_data?: object
  enabled?: boolean
}
