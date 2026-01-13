/**
 * Service de refresh automatique du token d'authentification
 * Utilise le refresh_token stocké dans un cookie httpOnly
 */

import { apiClient } from '@/lib/api-client'

let isRefreshing = false
let refreshPromise: Promise<void> | null = null

/**
 * Rafraîchit l'access token en utilisant le refresh token
 * Utilise un système de queue pour éviter les appels multiples simultanés
 */
export async function refreshAccessToken(): Promise<void> {
  // Si un refresh est déjà en cours, attendre qu'il se termine
  if (isRefreshing && refreshPromise) {
    return refreshPromise
  }

  isRefreshing = true
  refreshPromise = apiClient
    .post('/auth/refresh')
    .then(() => {
      // Refresh réussi, l'access_token cookie a été mis à jour par le backend
      console.log('[Auth] Access token refreshed successfully')
    })
    .catch((error) => {
      // Si le refresh échoue, rediriger vers login
      console.error('[Auth] Failed to refresh token:', error)
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
      throw error
    })
    .finally(() => {
      isRefreshing = false
      refreshPromise = null
    })

  return refreshPromise
}
