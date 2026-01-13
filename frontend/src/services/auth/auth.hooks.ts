"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { authService } from './auth.service'
import { extractErrorMessage } from '@/lib/error-handler'
import type { LoginDTO, RegisterDTO } from './auth.types'

/**
 * Hook pour récupérer l'utilisateur connecté
 * L'authentification est gérée par le cookie httpOnly
 */
export function useMe() {
  return useQuery({
    queryKey: ['user', 'me'],
    queryFn: authService.getMe,
    retry: false, // Ne pas retry si 401 (non authentifié)
  })
}

/**
 * Hook pour se connecter
 */
export function useLogin() {
  return useMutation({
    mutationFn: (dto: LoginDTO) => authService.login(dto),
    onSuccess: () => {
      // Les tokens sont gérés automatiquement par les cookies httpOnly
      // Plus besoin de stocker quoi que ce soit
      toast.success('Connexion réussie')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour s'inscrire
 */
export function useRegister() {
  return useMutation({
    mutationFn: (dto: RegisterDTO) => authService.register(dto),
    onSuccess: () => {
      // Les tokens sont gérés automatiquement par les cookies httpOnly
      // Plus besoin de stocker quoi que ce soit
      toast.success('Inscription réussie')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour se déconnecter
 */
export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => authService.logout(),
    onSuccess: () => {
      // Les cookies sont supprimés par le backend
      queryClient.clear()  // Vide tout le cache React Query
      toast.success('Déconnexion réussie')
      window.location.href = '/login'
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}
