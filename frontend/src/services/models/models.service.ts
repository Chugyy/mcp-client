import { apiClient } from '@/lib/api-client'
import type { Model, ModelWithService } from './models.types'

export const modelsService = {
  /**
   * Liste les modèles disponibles pour l'utilisateur connecté
   * (filtrés par providers avec clé API configurée, inclut logo_url)
   */
  async getAll(): Promise<ModelWithService[]> {
    const { data } = await apiClient.get('/models')
    return data
  },

  /**
   * Liste les modèles avec informations de service (JOIN)
   */
  async getAllWithService(): Promise<ModelWithService[]> {
    const { data } = await apiClient.get('/models/with-service')
    return data
  },

  /**
   * Récupère un modèle par ID
   */
  async getById(id: string): Promise<Model> {
    const { data } = await apiClient.get(`/models/${id}`)
    return data
  },
}

export const modelKeys = {
  all: ['models'] as const,
  lists: () => [...modelKeys.all, 'list'] as const,
  listsWithService: () => [...modelKeys.all, 'list-with-service'] as const,
  detail: (id: string) => [...modelKeys.all, 'detail', id] as const,
}
