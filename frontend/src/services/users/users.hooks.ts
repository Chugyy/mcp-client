"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { usersService, usersKeys } from './users.service'
import { extractErrorMessage } from '@/lib/error-handler'
import type { User, UpdateUserDTO, UpdatePermissionLevelDTO } from './users.types'

/**
 * Hook pour récupérer les informations de l'utilisateur connecté
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: usersKeys.me(),
    queryFn: () => usersService.getMe(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook pour mettre à jour les informations de l'utilisateur
 * Avec optimistic update pour UX fluide
 */
export function useUpdateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: UpdateUserDTO) => usersService.updateMe(dto),
    onMutate: async (dto) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: usersKeys.me() })
      const previousUser = queryClient.getQueryData<User>(usersKeys.me())

      if (previousUser) {
        queryClient.setQueryData<User>(usersKeys.me(), {
          ...previousUser,
          ...dto,
          preferences: { ...previousUser.preferences, ...dto.preferences },
        })
      }

      return { previousUser }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: usersKeys.me() })
      toast.success('Profil mis à jour avec succès')
    },
    onError: (error: any, _, context) => {
      // Rollback on error
      if (context?.previousUser) {
        queryClient.setQueryData(usersKeys.me(), context.previousUser)
      }
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour mettre à jour le niveau de permission
 * Avec optimistic update
 */
export function useUpdatePermissionLevel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: UpdatePermissionLevelDTO) => usersService.updatePermissionLevel(dto),
    onMutate: async (dto) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: usersKeys.me() })
      const previousUser = queryClient.getQueryData<User>(usersKeys.me())

      if (previousUser) {
        queryClient.setQueryData<User>(usersKeys.me(), {
          ...previousUser,
          permission_level: dto.permission_level,
        })
      }

      return { previousUser }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: usersKeys.me() })
      toast.success('Niveau de permission mis à jour')
    },
    onError: (error: any, _, context) => {
      // Rollback on error
      if (context?.previousUser) {
        queryClient.setQueryData(usersKeys.me(), context.previousUser)
      }
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour récupérer les modèles disponibles de l'utilisateur
 */
export function useMyModels() {
  return useQuery({
    queryKey: usersKeys.models(),
    queryFn: () => usersService.getMyModels(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

/**
 * Hook pour supprimer le compte de l'utilisateur
 */
export function useDeleteAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => usersService.deleteMe(),
    onSuccess: () => {
      queryClient.clear()
      toast.success('Compte supprimé avec succès')
      // Redirection vers /login gérée par le composant
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}
