import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

/**
 * Vérifie l'authentification côté serveur via les cookies httpOnly
 * Redirige vers /login si non authentifié
 *
 * @returns Objet contenant le token et userId
 */
export async function requireAuth() {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')
  const userId = cookieStore.get('user_id')

  if (!token || !userId) {
    redirect('/login')
  }

  return {
    token: token.value,
    userId: userId.value
  }
}

/**
 * Récupère les informations d'auth sans redirection
 * Utile pour les composants serveur optionnels
 *
 * @returns Objet avec token et userId ou null si non authentifié
 */
export async function getAuth() {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')
  const userId = cookieStore.get('user_id')

  if (!token || !userId) {
    return null
  }

  return {
    token: token.value,
    userId: userId.value
  }
}
