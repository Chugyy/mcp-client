import { apiClient } from '@/lib/api-client'
import type { User, UpdateUserDTO, UpdatePermissionLevelDTO } from './users.types'

// Query keys pour React Query
export const usersKeys = {
  all: ['users'] as const,
  me: () => [...usersKeys.all, 'me'] as const,
  models: () => [...usersKeys.all, 'models'] as const,
}

// Service API pour l'utilisateur connecté
export const usersService = {
  /**
   * GET /users/me - Récupère les informations de l'utilisateur connecté
   */
  async getMe(): Promise<User> {
    const { data } = await apiClient.get('/users/me')
    return data
  },

  /**
   * PATCH /users/me - Met à jour les informations de l'utilisateur
   */
  async updateMe(dto: UpdateUserDTO): Promise<User> {
    const { data } = await apiClient.patch('/users/me', dto)
    return data
  },

  /**
   * PATCH /users/me/permission_level - Met à jour le niveau de permission
   */
  async updatePermissionLevel(dto: UpdatePermissionLevelDTO): Promise<User> {
    const { data } = await apiClient.patch('/users/me/permission_level', dto)
    return data
  },

  /**
   * GET /users/me/models - Récupère les modèles disponibles pour l'utilisateur
   * (avec auto-sync si aucun modèle disponible)
   */
  async getMyModels(): Promise<any[]> {
    const { data } = await apiClient.get('/users/me/models')
    return data
  },

  /**
   * DELETE /users/me - Supprime le compte de l'utilisateur connecté
   */
  async deleteMe(): Promise<void> {
    await apiClient.delete('/users/me')
  },
}
