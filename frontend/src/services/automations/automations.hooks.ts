"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { automationService, automationKeys } from './automations.service'
import { extractErrorMessage } from '@/lib/error-handler'
import type { Automation } from './automations.types'

// Queries
export function useAutomations() {
  return useQuery({
    queryKey: automationKeys.lists(),
    queryFn: () => automationService.getAll(),
  })
}

export function useAutomation(id: string) {
  return useQuery({
    queryKey: automationKeys.detail(id),
    queryFn: () => automationService.getById(id),
    enabled: !!id,
  })
}

export function useAutomationExecutions(automationId: string) {
  return useQuery({
    queryKey: automationKeys.executions(automationId),
    queryFn: () => automationService.getExecutions(automationId),
    enabled: !!automationId,
    refetchInterval: (query) => {
      // Refetch toutes les 10s si une execution est en cours
      const data = query.state.data
      const hasRunning = data?.some((exec: any) => exec.status === 'running')
      return hasRunning ? 10000 : false
    },
  })
}

export function useExecutionLogs(executionId: string) {
  return useQuery({
    queryKey: automationKeys.executionLogs(executionId),
    queryFn: () => automationService.getExecutionLogs(executionId),
    enabled: !!executionId,
  })
}

export function useWorkflowSteps(automationId: string) {
  return useQuery({
    queryKey: automationKeys.workflowSteps(automationId),
    queryFn: () => automationService.getWorkflowSteps(automationId),
    enabled: !!automationId,
  })
}

// Mutations
export function useToggleAutomation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      automationService.toggleEnabled(id, enabled),
    onMutate: async ({ id, enabled }) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: automationKeys.all })

      const previousData = queryClient.getQueryData(automationKeys.lists())

      queryClient.setQueryData(automationKeys.lists(), (old: Automation[] | undefined) =>
        old?.map((item) => (item.id === id ? { ...item, enabled } : item))
      )

      return { previousData }
    },
    onSuccess: (_, { enabled }) => {
      queryClient.invalidateQueries({ queryKey: automationKeys.all })
      toast.success(enabled ? 'Automation activée' : 'Automation désactivée')
    },
    onError: (error: any, _, context) => {
      // Rollback
      if (context?.previousData) {
        queryClient.setQueryData(automationKeys.lists(), context.previousData)
      }
      toast.error(extractErrorMessage(error))
    },
  })
}

export function useDeleteAutomation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: string | { id: string; headers?: Record<string, string> }) => {
      if (typeof params === 'string') {
        return automationService.delete(params)
      }
      return automationService.delete(params.id, params.headers)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: automationKeys.all })
      toast.success('Automation supprimée')
    },
    onError: (error: any) => {
      // Ne pas afficher de toast si c'est une erreur 409 (cascade delete)
      if (error.response?.status === 409) {
        throw error // Re-throw pour que le composant puisse gérer
      }
      toast.error(extractErrorMessage(error))
    },
  })
}
