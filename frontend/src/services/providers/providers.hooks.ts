"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { providersService, providersKeys } from './providers.service'
import { extractErrorMessage } from '@/lib/error-handler'
import type {
  Service,
  UserProvider,
  CreateUserProviderDTO,
  UpdateUserProviderDTO,
} from './providers.types'

/**
 * Hook pour lister les services LLM disponibles
 * @param provider - Filtre par provider(s) : 'openai' | ['openai', 'anthropic'] | undefined
 * @example
 * useServices()                          // Tous les services
 * useServices('openai')                  // OpenAI uniquement
 * useServices(['openai', 'anthropic'])   // OpenAI + Anthropic
 */
export function useServices(provider?: string | string[]) {
  return useQuery({
    queryKey: providersKeys.servicesList(provider),
    queryFn: () => providersService.getServices(provider),
  })
}

/**
 * Hook pour lister les providers disponibles dans le système
 */
export function useAvailableProviders() {
  return useQuery({
    queryKey: providersKeys.availableProviders(),
    queryFn: () => providersService.getAvailableProviders(),
  })
}

/**
 * Hook pour lister les providers configurés par l'utilisateur
 */
export function useUserProviders() {
  return useQuery({
    queryKey: providersKeys.userProvidersList(),
    queryFn: () => providersService.getUserProviders(),
  })
}

/**
 * Hook pour récupérer un provider spécifique
 */
export function useUserProvider(id: string) {
  return useQuery({
    queryKey: providersKeys.userProviderDetail(id),
    queryFn: () => providersService.getUserProvider(id),
    enabled: !!id,
  })
}

/**
 * Hook pour créer un provider (activer un service LLM pour l'utilisateur)
 */
export function useCreateUserProvider() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: CreateUserProviderDTO) => providersService.createUserProvider(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: providersKeys.userProviders() })
      // Invalider les modèles car de nouveaux modèles seront disponibles après sync
      queryClient.invalidateQueries({ queryKey: ['models'] })
      toast.success('Provider configuré avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour mettre à jour un provider (toggle ON/OFF ou changer la clé API)
 * Avec optimistic update pour UX fluide
 */
export function useUpdateUserProvider() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateUserProviderDTO }) =>
      providersService.updateUserProvider(id, data),
    onMutate: async ({ id, data }) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: providersKeys.userProviders() })
      const previousData = queryClient.getQueryData(providersKeys.userProvidersList())

      if (previousData) {
        queryClient.setQueryData(providersKeys.userProvidersList(), (old: any) =>
          old?.map((provider: UserProvider) =>
            provider.id === id ? { ...provider, ...data } : provider
          )
        )
      }

      return { previousData }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: providersKeys.userProviders() })
      // Invalider les modèles car la liste peut changer selon l'état du provider
      queryClient.invalidateQueries({ queryKey: ['models'] })
      toast.success('Provider mis à jour avec succès')
    },
    onError: (error: any, _, context) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(providersKeys.userProvidersList(), context.previousData)
      }
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour supprimer un provider (avec optimistic update)
 */
export function useDeleteUserProvider() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => providersService.deleteUserProvider(id),
    onMutate: async (id) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: providersKeys.userProviders() })
      const previousData = queryClient.getQueryData(providersKeys.userProvidersList())

      if (previousData) {
        queryClient.setQueryData(providersKeys.userProvidersList(), (old: any) =>
          old?.filter((provider: UserProvider) => provider.id !== id)
        )
      }

      return { previousData }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: providersKeys.userProviders() })
      // Invalider les modèles car ils ne seront plus disponibles
      queryClient.invalidateQueries({ queryKey: ['models'] })
      toast.success('Provider supprimé avec succès')
    },
    onError: (error: any, _, context) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(providersKeys.userProvidersList(), context.previousData)
      }
      toast.error(extractErrorMessage(error))
    },
  })
}
