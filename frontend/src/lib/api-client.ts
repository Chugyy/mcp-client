"use client"

import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { QueryClient } from '@tanstack/react-query'

// Configuration de base
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Instance Axios avec configuration
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
  withCredentials: true,  // Permet d'envoyer les cookies
})

// Le token est envoyé automatiquement via le cookie httpOnly (access_token)
// Pas besoin d'intercepteur pour ajouter le token manuellement

// Intercepteur pour gérer le refresh automatique du token
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Si erreur 401 et que la requête n'a pas déjà été réessayée
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Éviter de refresh sur les endpoints d'auth
      if (originalRequest.url?.includes('/auth/login') ||
          originalRequest.url?.includes('/auth/register') ||
          originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error)
      }

      originalRequest._retry = true

      try {
        // Import dynamique pour éviter les dépendances circulaires
        const { refreshAccessToken } = await import('@/services/auth/auth.refresh')

        // Tenter de refresh le token
        await refreshAccessToken()

        // Réessayer la requête originale avec le nouveau token
        return apiClient(originalRequest)
      } catch (refreshError) {
        // Le refresh a échoué, redirection vers login géré par auth.refresh.ts
        return Promise.reject(refreshError)
      }
    }

    // Pour toutes les autres erreurs, rejeter
    return Promise.reject(error)
  }
)

// Configuration React Query Client
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
})
