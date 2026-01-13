import { apiClient } from '@/lib/api-client'
import type {
  Service,
  UserProvider,
  CreateUserProviderDTO,
  UpdateUserProviderDTO,
} from './providers.types'

// Query keys pour React Query
export const providersKeys = {
  all: ['providers'] as const,
  services: () => [...providersKeys.all, 'services'] as const,
  servicesList: (provider?: string | string[]) => {
    // Normaliser pour le cache
    const normalizedProvider = Array.isArray(provider)
      ? provider.sort().join(',')  // ['anthropic', 'openai'] => 'anthropic,openai'
      : provider
    return [...providersKeys.services(), 'list', normalizedProvider] as const
  },
  availableProviders: () => [...providersKeys.services(), 'available'] as const,
  userProviders: () => [...providersKeys.all, 'user-providers'] as const,
  userProvidersList: () => [...providersKeys.userProviders(), 'list'] as const,
  userProviderDetail: (id: string) => [...providersKeys.userProviders(), 'detail', id] as const,
}

// Service API pour les providers LLM
export const providersService = {
  /**
   * GET /services - Liste tous les services avec filtre optionnel
   * @param provider - Filtre par provider(s) : string unique ou tableau
   * @example
   * getServices('openai')                    // Un seul
   * getServices(['openai', 'anthropic'])     // Plusieurs
   * getServices()                            // Tous
   */
  async getServices(provider?: string | string[]): Promise<Service[]> {
    // Convertir tableau en CSV si nécessaire
    let providerParam: string | undefined

    if (Array.isArray(provider)) {
      providerParam = provider.join(',')  // ['openai', 'anthropic'] => 'openai,anthropic'
    } else {
      providerParam = provider
    }

    const { data } = await apiClient.get('/services', {
      params: providerParam ? { provider: providerParam } : undefined,
    })
    return data
  },

  /**
   * GET /services/providers - Liste tous les providers disponibles
   * Utile pour construire des filtres dynamiques
   */
  async getAvailableProviders(): Promise<string[]> {
    const { data } = await apiClient.get('/services/providers')
    return data
  },

  /**
   * GET /providers - Liste les providers configurés pour l'utilisateur
   */
  async getUserProviders(): Promise<UserProvider[]> {
    const { data } = await apiClient.get('/providers')
    return data
  },

  /**
   * GET /providers/{id} - Récupère un provider par ID
   */
  async getUserProvider(id: string): Promise<UserProvider> {
    const { data } = await apiClient.get(`/providers/${id}`)
    return data
  },

  /**
   * POST /providers - Crée un provider pour l'utilisateur
   */
  async createUserProvider(dto: CreateUserProviderDTO): Promise<UserProvider> {
    const { data } = await apiClient.post('/providers', dto)
    return data
  },

  /**
   * PATCH /providers/{id} - Met à jour un provider
   */
  async updateUserProvider(id: string, dto: UpdateUserProviderDTO): Promise<UserProvider> {
    const { data } = await apiClient.patch(`/providers/${id}`, dto)
    return data
  },

  /**
   * DELETE /providers/{id} - Supprime un provider
   */
  async deleteUserProvider(id: string): Promise<void> {
    await apiClient.delete(`/providers/${id}`)
  },
}
