import type { Resource } from '@/services/resources/resources.types'
import type { MCPServerWithTools, MCPTool } from '@/services/mcp/mcp.types'

/**
 * MCP Tool configuration
 * Structure conforme au backend : utilise "id" et non "tool_id"
 */
export interface AgentMCPTool {
  id: string
  name?: string | null
  description?: string | null
  enabled: boolean
}

/**
 * MCP Server configuration for an agent
 */
export interface AgentMCPConfig {
  id?: string
  server_id: string
  enabled: boolean
  tools: AgentMCPTool[]
}

/**
 * Resource configuration for an agent
 */
export interface AgentResource {
  id: string
  enabled: boolean
}

/**
 * Agent - Complete agent entity with all properties including metadata
 */
export interface Agent {
  id: string
  user_id: string
  name: string
  description: string | null
  system_prompt: string
  tags: string[]
  enabled: boolean
  is_system: boolean
  avatar_url?: string
  mcp_configs?: AgentMCPConfig[]
  resources?: AgentResource[]
  created_at: string
  updated_at: string
}

/**
 * CreateAgentDTO - Data transfer object for creating a new agent
 * Required: name, system_prompt
 * Optional: description, tags, enabled, mcp_configs, resources
 */
export interface CreateAgentDTO {
  name: string
  description?: string | null
  system_prompt: string
  tags?: string[]
  enabled?: boolean
  mcp_configs?: AgentMCPConfig[]
  resources?: AgentResource[]
}

/**
 * UpdateAgentDTO - Data transfer object for updating an existing agent
 * All fields are optional (partial update)
 */
export interface UpdateAgentDTO {
  name?: string | null
  description?: string | null
  system_prompt?: string | null
  tags?: string[] | null
  enabled?: boolean | null
  mcp_configs?: AgentMCPConfig[]
  resources?: AgentResource[]
}

/**
 * Types hydratés pour l'UI - combinent relation + entité complète
 */

/**
 * AgentResourceHydrated - Resource complète avec le statut enabled de la relation
 * Utilisé pour l'affichage dans l'UI
 */
export interface AgentResourceHydrated extends Resource {
  enabled: boolean
}

/**
 * AgentMCPToolHydrated - Tool complet avec le statut enabled de la relation
 * Enrichi avec les données complètes du MCPTool depuis le serveur
 */
export interface AgentMCPToolHydrated {
  id: string
  name: string
  description: string | null
  enabled: boolean
}

/**
 * AgentMCPConfigHydrated - Config MCP avec server et tools complets
 * Utilisé pour l'affichage dans l'UI
 */
export interface AgentMCPConfigHydrated {
  id?: string
  server_id: string
  server_name: string
  server_description: string | null
  enabled: boolean
  tools: AgentMCPToolHydrated[]
}
