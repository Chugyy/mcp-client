import { apiClient } from '@/lib/api-client'
import type {
  Resource,
  Upload,
  CreateResourceDTO,
  UpdateResourceDTO,
} from './resources.types'

// Query keys pour React Query
export const resourceKeys = {
  all: ['resources'] as const,
  lists: () => [...resourceKeys.all, 'list'] as const,
  list: (filters?: { enabled_only?: boolean }) =>
    [...resourceKeys.lists(), filters] as const,
  detail: (id: string) => [...resourceKeys.all, 'detail', id] as const,
  uploads: (resourceId: string) => [...resourceKeys.all, resourceId, 'uploads'] as const,
}

// Service API pour les ressources
export const resourceService = {
  /**
   * GET /resources - Liste toutes les ressources
   */
  async getAll(params?: { enabled_only?: boolean }): Promise<Resource[]> {
    const { data } = await apiClient.get('/resources', { params })
    return data
  },

  /**
   * GET /resources/{resource_id} - Récupère une ressource par ID
   */
  async getById(id: string): Promise<Resource> {
    const { data } = await apiClient.get(`/resources/${id}`)
    return data
  },

  /**
   * POST /resources - Crée une nouvelle ressource
   */
  async create(dto: CreateResourceDTO): Promise<Resource> {
    const { data } = await apiClient.post('/resources', dto)
    return data
  },

  /**
   * PATCH /resources/{resource_id} - Met à jour une ressource
   */
  async update(id: string, dto: UpdateResourceDTO): Promise<Resource> {
    const { data } = await apiClient.patch(`/resources/${id}`, dto)
    return data
  },

  /**
   * DELETE /resources/{resource_id} - Supprime une ressource
   */
  async delete(id: string, headers?: Record<string, string>): Promise<void> {
    await apiClient.delete(`/resources/${id}`, { headers })
  },

  /**
   * GET /resources/{resource_id}/uploads - Liste tous les uploads d'une ressource
   */
  async getUploads(resourceId: string): Promise<Upload[]> {
    const { data } = await apiClient.get(`/resources/${resourceId}/uploads`)
    return data
  },

  /**
   * POST /resources/{resource_id}/ingest - Déclenche l'ingestion d'une ressource
   */
  async ingest(resourceId: string): Promise<{ success: boolean; message: string }> {
    const { data } = await apiClient.post(`/resources/${resourceId}/ingest`)
    return data
  },

  /**
   * POST /uploads - Upload un fichier pour une ressource
   */
  async uploadFile(resourceId: string, file: File): Promise<Upload> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('upload_type', 'resource')
    formData.append('resource_id', resourceId)

    const { data } = await apiClient.post('/uploads', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },

  /**
   * DELETE /uploads/{uploadId} - Supprime un upload
   */
  async deleteUpload(uploadId: string): Promise<void> {
    await apiClient.delete(`/uploads/${uploadId}`)
  }
}
