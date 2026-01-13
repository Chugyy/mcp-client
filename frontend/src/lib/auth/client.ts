"use client"

/**
 * Récupère le user_id depuis localStorage (côté client uniquement)
 * Compatible SSR - retourne null si window non disponible
 *
 * @returns user_id ou null
 */
export function getUserId(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('user_id')
}

/**
 * Définit le user_id dans localStorage (côté client uniquement)
 *
 * @param userId - L'identifiant utilisateur à stocker
 */
export function setUserId(userId: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem('user_id', userId)
}

/**
 * Nettoie les informations d'authentification côté client
 * Supprime user_id du localStorage
 */
export function clearAuth(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem('user_id')
}
