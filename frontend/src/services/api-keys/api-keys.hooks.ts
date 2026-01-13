"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiKeysService, apiKeysKeys } from './api-keys.service'
import { extractErrorMessage } from '@/lib/error-handler'
import type {
  ApiKey,
  CreateApiKeyDTO,
  UpdateApiKeyDTO,
} from './api-keys.types'

/**
 * Hook pour lister toutes les clés API de l'utilisateur
 */
export function useApiKeys() {
  return useQuery({
    queryKey: apiKeysKeys.list(),
    queryFn: () => apiKeysService.getAll(),
  })
}

/**
 * Hook pour récupérer une clé API par ID
 */
export function useApiKey(id: string) {
  return useQuery({
    queryKey: apiKeysKeys.detail(id),
    queryFn: () => apiKeysService.getById(id),
    enabled: !!id,
  })
}

/**
 * Hook pour créer une nouvelle clé API chiffrée
 * IMPORTANT: La valeur en clair est retournée uniquement à la création
 */
export function useCreateApiKey() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: CreateApiKeyDTO) => apiKeysService.create(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeysKeys.all })
      // Note: On ne toast pas ici car cette action fait partie d'un flow plus large
      // Le toast sera affiché quand le provider sera créé avec succès
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour mettre à jour une clé API (rotation de clé)
 */
export function useUpdateApiKey() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateApiKeyDTO }) =>
      apiKeysService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeysKeys.all })
      toast.success('Clé API mise à jour avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour supprimer une clé API
 */
export function useDeleteApiKey() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => apiKeysService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: apiKeysKeys.all })
      // Note: Le toast est géré dans le composant parent (après suppression du provider)
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}
