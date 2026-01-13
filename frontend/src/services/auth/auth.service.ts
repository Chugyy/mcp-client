import { apiClient } from '@/lib/api-client'
import type { LoginDTO, RegisterDTO, AuthResponse, User } from './auth.types'

// Service API pour l'authentification
export const authService = {
  /**
   * Connexion utilisateur
   */
  async login(dto: LoginDTO): Promise<AuthResponse> {
    console.log('📡 Sending login request to:', apiClient.defaults.baseURL + '/auth/login', dto);
    const { data } = await apiClient.post('/auth/login', dto)
    console.log('📥 Login response:', data);
    return data
  },

  /**
   * Inscription utilisateur
   */
  async register(dto: RegisterDTO): Promise<AuthResponse> {
    const { data } = await apiClient.post('/auth/register', dto)
    return data
  },

  /**
   * Récupère les infos de l'utilisateur connecté
   */
  async getMe(): Promise<User> {
    const { data } = await apiClient.get('/auth/me')
    return data
  },

  /**
   * Déconnexion utilisateur
   */
  async logout(): Promise<void> {
    await apiClient.post('/auth/logout')
  },
}
