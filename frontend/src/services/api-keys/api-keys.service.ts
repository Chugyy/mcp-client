import { apiClient } from '@/lib/api-client'
import type {
  ApiKey,
  ApiKeyWithValue,
  CreateApiKeyDTO,
  UpdateApiKeyDTO,
} from './api-keys.types'

// Query keys pour React Query
export const apiKeysKeys = {
  all: ['api-keys'] as const,
  list: () => [...apiKeysKeys.all, 'list'] as const,
  detail: (id: string) => [...apiKeysKeys.all, 'detail', id] as const,
}

// Service API pour les clés API
export const apiKeysService = {
  /**
   * POST /api-keys - Crée une nouvelle clé API chiffrée
   * La valeur en clair est retournée uniquement à la création
   */
  async create(dto: CreateApiKeyDTO): Promise<ApiKeyWithValue> {
    const { data } = await apiClient.post('/api-keys', dto)
    return data
  },

  /**
   * GET /api-keys - Liste toutes les clés API de l'utilisateur
   */
  async getAll(): Promise<ApiKey[]> {
    const { data } = await apiClient.get('/api-keys')
    return data
  },

  /**
   * GET /api-keys/{id} - Récupère une clé API par ID
   */
  async getById(id: string): Promise<ApiKey> {
    const { data } = await apiClient.get(`/api-keys/${id}`)
    return data
  },

  /**
   * PATCH /api-keys/{id} - Met à jour une clé API (rotation)
   */
  async update(id: string, dto: UpdateApiKeyDTO): Promise<ApiKey> {
    const { data } = await apiClient.patch(`/api-keys/${id}`, dto)
    return data
  },

  /**
   * DELETE /api-keys/{id} - Supprime une clé API
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`/api-keys/${id}`)
  },
}
