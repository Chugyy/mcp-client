import { apiClient } from '@/lib/api-client'
import type {
  MCPServer,
  MCPServerWithTools,
  MCPTool,
  MCPConfiguration,
  CreateMCPServerDTO,
  UpdateMCPServerDTO,
  CreateMCPToolDTO,
  CreateMCPConfigurationDTO,
} from './mcp.types'

// Query keys pour React Query
export const mcpKeys = {
  all: ['mcp'] as const,
  servers: () => [...mcpKeys.all, 'servers'] as const,
  serversList: (filters?: { enabled_only?: boolean; with_tools?: boolean }) =>
    [...mcpKeys.servers(), 'list', filters] as const,
  serverDetail: (id: string) => [...mcpKeys.servers(), 'detail', id] as const,
  tools: (serverId: string) => [...mcpKeys.servers(), serverId, 'tools'] as const,
  configurations: (agentId: string) => [...mcpKeys.all, 'configurations', agentId] as const,
}

// Service API pour les serveurs MCP
export const mcpService = {
  /**
   * GET /mcp/servers - Liste tous les serveurs MCP
   */
  async getServers(params?: { enabled_only?: boolean; with_tools?: boolean }): Promise<MCPServer[] | MCPServerWithTools[]> {
    const { data } = await apiClient.get('/mcp/servers', { params })
    return data
  },

  /**
   * GET /mcp/servers/{server_id} - Récupère un serveur MCP par ID
   */
  async getServer(id: string): Promise<MCPServer> {
    const { data } = await apiClient.get(`/mcp/servers/${id}`)
    return data
  },

  /**
   * POST /mcp/servers - Crée un nouveau serveur MCP
   */
  async createServer(dto: CreateMCPServerDTO): Promise<MCPServer> {
    const { data } = await apiClient.post('/mcp/servers', dto)
    return data
  },

  /**
   * PATCH /mcp/servers/{server_id} - Met à jour un serveur MCP
   */
  async updateServer(id: string, dto: UpdateMCPServerDTO): Promise<MCPServer> {
    const { data } = await apiClient.patch(`/mcp/servers/${id}`, dto)
    return data
  },

  /**
   * DELETE /mcp/servers/{server_id} - Supprime un serveur MCP
   */
  async deleteServer(id: string, headers?: Record<string, string>): Promise<void> {
    await apiClient.delete(`/mcp/servers/${id}`, { headers })
  },

  /**
   * POST /mcp/servers/{server_id}/sync - Synchronise les tools d'un serveur MCP
   */
  async syncServer(id: string): Promise<MCPServer> {
    const { data } = await apiClient.post(`/mcp/servers/${id}/sync`)
    return data
  },

  /**
   * GET /mcp/servers/{server_id}/tools - Liste tous les outils d'un serveur MCP
   */
  async getTools(serverId: string): Promise<MCPTool[]> {
    const { data } = await apiClient.get(`/mcp/servers/${serverId}/tools`)
    return data
  },

  /**
   * POST /mcp/servers/{server_id}/tools - Crée manuellement un outil MCP
   */
  async createTool(serverId: string, dto: CreateMCPToolDTO): Promise<MCPTool> {
    const { data } = await apiClient.post(`/mcp/servers/${serverId}/tools`, dto)
    return data
  },

  /**
   * PATCH /mcp/servers/{server_id}/tools/{tool_id} - Met à jour un outil MCP
   */
  async updateTool(serverId: string, toolId: string, dto: { enabled?: boolean }): Promise<MCPTool> {
    const { data } = await apiClient.patch(`/mcp/servers/${serverId}/tools/${toolId}`, dto)
    return data
  },

  /**
   * GET /mcp/servers/agents/{agent_id}/configurations - Liste les configurations MCP d'un agent
   */
  async getConfigurations(agentId: string): Promise<MCPConfiguration[]> {
    const { data } = await apiClient.get(`/mcp/servers/agents/${agentId}/configurations`)
    return data
  },

  /**
   * POST /mcp/servers/agents/{agent_id}/configurations - Crée une configuration MCP pour un agent
   */
  async createConfiguration(agentId: string, dto: CreateMCPConfigurationDTO): Promise<MCPConfiguration> {
    const { data } = await apiClient.post(`/mcp/servers/agents/${agentId}/configurations`, dto)
    return data
  },

  /**
   * DELETE /mcp/servers/configurations/{config_id} - Supprime une configuration MCP
   */
  async deleteConfiguration(configId: string): Promise<void> {
    await apiClient.delete(`/mcp/servers/configurations/${configId}`)
  },
}
