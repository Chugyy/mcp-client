import { apiClient } from '@/lib/api-client'
import type { Agent, CreateAgentDTO, UpdateAgentDTO } from './agents.types'

// Query keys pour React Query
export const agentKeys = {
  all: ['agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  detail: (id: string) => [...agentKeys.all, 'detail', id] as const,
}

// Fonctions API
export const agentsService = {
  async getAll(): Promise<Agent[]> {
    const { data } = await apiClient.get('/agents')
    return data
  },

  async getById(id: string): Promise<Agent> {
    const { data } = await apiClient.get(`/agents/${id}`)
    return data
  },

  async create(dto: CreateAgentDTO, avatar?: File): Promise<Agent> {
    const formData = new FormData()
    formData.append('name', dto.name)
    formData.append('system_prompt', dto.system_prompt)
    if (dto.description) formData.append('description', dto.description)
    if (dto.tags && dto.tags.length > 0) formData.append('tags', JSON.stringify(dto.tags))
    formData.append('enabled', String(dto.enabled ?? true))
    if (dto.mcp_configs && dto.mcp_configs.length > 0) formData.append('mcp_configs', JSON.stringify(dto.mcp_configs))
    if (dto.resources && dto.resources.length > 0) formData.append('resources', JSON.stringify(dto.resources))
    if (avatar) formData.append('avatar', avatar)

    const { data } = await apiClient.post('/agents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },

  async update(id: string, dto: UpdateAgentDTO, avatar?: File): Promise<Agent> {
    const formData = new FormData()
    if (dto.name !== undefined) formData.append('name', dto.name || '')
    if (dto.system_prompt !== undefined) formData.append('system_prompt', dto.system_prompt || '')
    if (dto.description !== undefined) formData.append('description', dto.description || '')
    if (dto.tags !== undefined) formData.append('tags', JSON.stringify(dto.tags))
    if (dto.enabled !== undefined) formData.append('enabled', String(dto.enabled))
    if (dto.mcp_configs !== undefined) formData.append('mcp_configs', JSON.stringify(dto.mcp_configs))
    if (dto.resources !== undefined) formData.append('resources', JSON.stringify(dto.resources))
    if (avatar) formData.append('avatar', avatar)

    const { data } = await apiClient.patch(`/agents/${id}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },

  async delete(id: string, headers?: Record<string, string>): Promise<void> {
    await apiClient.delete(`/agents/${id}`, { headers })
  },

  async duplicate(id: string): Promise<Agent> {
    const { data } = await apiClient.post(`/agents/${id}/duplicate`)
    return data
  },

  async toggle(id: string, enabled: boolean): Promise<Agent> {
    const { data } = await apiClient.patch(`/agents/${id}`, { enabled })
    return data
  },
}
