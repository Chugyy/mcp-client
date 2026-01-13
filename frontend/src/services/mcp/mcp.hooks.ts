"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { mcpService, mcpKeys } from './mcp.service'
import { extractErrorMessage } from '@/lib/error-handler'
import type {
  CreateMCPServerDTO,
  UpdateMCPServerDTO,
  CreateMCPToolDTO,
  CreateMCPConfigurationDTO,
  MCPServer,
  MCPServerWithTools,
  MCPTool,
  MCPConfiguration
} from './mcp.types'

/**
 * Hook pour lister tous les serveurs MCP (avec options et polling)
 */
export function useMCPServers(params?: { enabled_only?: boolean; with_tools?: boolean; polling?: boolean }) {
  const { polling = true, ...serviceParams } = params || {}

  return useQuery({
    queryKey: mcpKeys.serversList(serviceParams),
    queryFn: () => mcpService.getServers(serviceParams),
    refetchInterval: polling ? 2000 : false, // Polling toutes les 2s par défaut
  })
}

/**
 * Hook pour récupérer un serveur spécifique
 */
export function useMCPServer(id: string) {
  return useQuery({
    queryKey: mcpKeys.serverDetail(id),
    queryFn: () => mcpService.getServer(id),
    enabled: !!id,
  })
}

/**
 * Hook pour lister les tools d'un serveur
 */
export function useMCPTools(serverId: string) {
  return useQuery({
    queryKey: mcpKeys.tools(serverId),
    queryFn: () => mcpService.getTools(serverId),
    enabled: !!serverId,
  })
}

/**
 * Hook pour lister les configurations d'un agent
 */
export function useMCPConfigurations(agentId: string) {
  return useQuery({
    queryKey: mcpKeys.configurations(agentId),
    queryFn: () => mcpService.getConfigurations(agentId),
    enabled: !!agentId,
  })
}

/**
 * Hook pour créer un nouveau serveur MCP (avec gestion OAuth popup)
 */
export function useCreateMCPServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: CreateMCPServerDTO) => mcpService.createServer(dto),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers() })

      // Gestion OAuth : si status='pending_authorization', ouvrir popup
      if (data.status === 'pending_authorization' && data.status_message) {
        window.open(data.status_message, '_blank', 'width=600,height=700')
      }

      toast.success('Serveur MCP créé avec succès')
    },
    onError: (error: any) => {
      const message = extractErrorMessage(error)
      toast.error(message)
    },
  })
}

/**
 * Hook pour mettre à jour un serveur MCP (avec optimistic update)
 */
export function useUpdateMCPServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateMCPServerDTO }) =>
      mcpService.updateServer(id, data),
    onMutate: async ({ id, data }) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: mcpKeys.servers() })
      const previousData = queryClient.getQueryData(mcpKeys.serversList())

      if (previousData) {
        queryClient.setQueryData(mcpKeys.serversList(), (old: any) =>
          old?.map((server: MCPServer) =>
            server.id === id ? { ...server, ...data } : server
          )
        )
      }

      return { previousData }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers() })
      toast.success('Serveur MCP mis à jour avec succès')
    },
    onError: (error: any, _, context) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(mcpKeys.serversList(), context.previousData)
      }
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour supprimer un serveur MCP (avec optimistic update)
 */
export function useDeleteMCPServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: string | { id: string; headers?: Record<string, string> }) => {
      // Support ancien format (string) et nouveau format (objet)
      if (typeof params === 'string') {
        return mcpService.deleteServer(params)
      }
      return mcpService.deleteServer(params.id, params.headers)
    },
    onMutate: async (params) => {
      // Extract id from params
      const id = typeof params === 'string' ? params : params.id

      // Optimistic update
      await queryClient.cancelQueries({ queryKey: mcpKeys.servers() })
      const previousData = queryClient.getQueryData(mcpKeys.serversList())

      if (previousData) {
        queryClient.setQueryData(mcpKeys.serversList(), (old: any) =>
          old?.filter((server: MCPServer) => server.id !== id)
        )
      }

      return { previousData }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers() })
      toast.success('Serveur MCP supprimé avec succès')
    },
    onError: (error: any, _, context) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(mcpKeys.serversList(), context.previousData)
      }
      // Ne pas afficher de toast si c'est un 409 (géré par le composant)
      if (error.response?.status !== 409) {
        toast.error(extractErrorMessage(error))
      }
    },
  })
}

/**
 * Hook pour synchroniser un serveur MCP
 * Retourne toujours 200 OK, le status du serveur est dans data.status
 */
export function useSyncMCPServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => mcpService.syncServer(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers() })
      queryClient.invalidateQueries({ queryKey: mcpKeys.tools(data.id) })

      // Interpréter le status retourné par le backend
      if (data.status === 'unreachable') {
        toast.error(data.status_message || 'Le serveur MCP est injoignable')
      } else if (data.status === 'failed') {
        toast.error(data.status_message || 'Erreur d\'authentification du serveur MCP')
      } else if (data.status === 'pending_authorization') {
        // Gestion OAuth : ouvrir popup si nécessaire
        if (data.status_message) {
          window.open(data.status_message, '_blank', 'width=600,height=700')
          toast.info('Veuillez autoriser l\'accès OAuth')
        } else {
          toast.info('Autorisation OAuth requise')
        }
      } else if (data.status === 'active') {
        toast.success('Serveur synchronisé avec succès')
      } else {
        // Status inconnu ou pending
        toast.info(data.status_message || 'Synchronisation en cours')
      }
    },
    onError: (error: any) => {
      // Gestion des vraies erreurs réseau ou serveur backend down
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour créer un tool MCP
 */
export function useCreateMCPTool() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ serverId, data }: { serverId: string; data: CreateMCPToolDTO }) =>
      mcpService.createTool(serverId, data),
    onSuccess: (_, { serverId }) => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.tools(serverId) })
      toast.success('Tool créé avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour mettre à jour un tool MCP (avec optimistic update)
 */
export function useUpdateMCPTool() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ serverId, toolId, data }: { serverId: string; toolId: string; data: { enabled?: boolean } }) =>
      mcpService.updateTool(serverId, toolId, data),
    onMutate: async ({ serverId, toolId, data }) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: mcpKeys.servers() })
      const previousData = queryClient.getQueryData(mcpKeys.serversList({ with_tools: true }))

      if (previousData) {
        queryClient.setQueryData(mcpKeys.serversList({ with_tools: true }), (old: any) =>
          old?.map((server: MCPServerWithTools) => {
            if (server.id === serverId && server.tools) {
              return {
                ...server,
                tools: server.tools.map((tool: MCPTool) =>
                  tool.id === toolId ? { ...tool, ...data } : tool
                )
              }
            }
            return server
          })
        )
      }

      return { previousData }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers() })
      toast.success('Tool mis à jour avec succès')
    },
    onError: (error: any, _, context) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(mcpKeys.serversList({ with_tools: true }), context.previousData)
      }
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour créer une configuration MCP pour un agent
 */
export function useCreateMCPConfiguration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ agentId, data }: { agentId: string; data: CreateMCPConfigurationDTO }) =>
      mcpService.createConfiguration(agentId, data),
    onSuccess: (_, { agentId }) => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.configurations(agentId) })
      toast.success('Configuration créée avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour supprimer une configuration MCP
 */
export function useDeleteMCPConfiguration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ configId, agentId }: { configId: string; agentId: string }) =>
      mcpService.deleteConfiguration(configId),
    onSuccess: (_, { agentId }) => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.configurations(agentId) })
      toast.success('Configuration supprimée avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}
