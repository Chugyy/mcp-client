'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { agentsService, agentKeys } from './agents.service'
import { extractErrorMessage } from '@/lib/error-handler'
import type { Agent, CreateAgentDTO, UpdateAgentDTO } from './agents.types'

/**
 * Hook pour récupérer la liste de tous les agents
 */
export function useAgents() {
  return useQuery({
    queryKey: agentKeys.lists(),
    queryFn: agentsService.getAll,
  })
}

/**
 * Hook pour récupérer un agent par son ID
 */
export function useAgent(id: string) {
  return useQuery({
    queryKey: agentKeys.detail(id),
    queryFn: () => agentsService.getById(id),
    enabled: !!id,
  })
}

/**
 * Hook pour créer un nouvel agent
 */
export function useCreateAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ dto, avatar }: { dto: CreateAgentDTO; avatar?: File }) =>
      agentsService.create(dto, avatar),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
      toast.success('Agent créé avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour mettre à jour un agent avec optimistic update
 */
export function useUpdateAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data, avatar }: { id: string; data: UpdateAgentDTO; avatar?: File }) =>
      agentsService.update(id, data, avatar),
    onMutate: async ({ id, data }) => {
      // Annuler les requêtes en cours
      await queryClient.cancelQueries({ queryKey: agentKeys.lists() })

      // Sauvegarder les données précédentes
      const previousData = queryClient.getQueryData(agentKeys.lists())

      // Mise à jour optimiste de la liste
      queryClient.setQueryData(agentKeys.lists(), (old: Agent[]) =>
        old.map((item) => (item.id === id ? { ...item, ...data } : item))
      )

      return { previousData }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
      toast.success('Agent mis à jour')
    },
    onError: (error: any, _, context) => {
      // Rollback en cas d'erreur
      if (context?.previousData) {
        queryClient.setQueryData(agentKeys.lists(), context.previousData)
      }
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour supprimer un agent
 */
export function useDeleteAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: string | { id: string; headers?: Record<string, string> }) => {
      // Support ancien format (string) et nouveau format (objet)
      if (typeof params === 'string') {
        return agentsService.delete(params)
      }
      return agentsService.delete(params.id, params.headers)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
      toast.success('Agent supprimé')
    },
    onError: (error: any) => {
      // Ne pas afficher de toast si c'est un 409 (géré par le composant)
      if (error.response?.status !== 409) {
        toast.error(extractErrorMessage(error))
      }
    },
  })
}

/**
 * Hook pour dupliquer un agent
 */
export function useDuplicateAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: agentsService.duplicate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
      toast.success('Agent dupliqué avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour activer/désactiver un agent
 */
export function useToggleAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      agentsService.toggle(id, enabled),
    onSuccess: (_, { enabled }) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
      toast.success(enabled ? 'Agent activé' : 'Agent désactivé')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}
