"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useCallback } from 'react'
import { toast } from 'sonner'
import { chatService, chatKeys } from './chats.service'
import { extractErrorMessage } from '@/lib/error-handler'
import type {
  ChatCreate,
  MessageCreate,
  Source,
} from './chats.types'

// Ré-exporter chatKeys pour utilisation dans les composants
export { chatKeys }

// ===== HOOKS GET (useQuery) =====

/**
 * Hook pour récupérer la liste des chats de l'utilisateur.
 */
export function useChats() {
  return useQuery({
    queryKey: chatKeys.lists(),
    queryFn: chatService.getChats,
  })
}

/**
 * Hook pour récupérer un chat par ID.
 */
export function useChat(id: string | null) {
  return useQuery({
    queryKey: chatKeys.detail(id!),
    queryFn: () => chatService.getChat(id!),
    enabled: !!id,
  })
}

/**
 * Hook pour récupérer les messages d'un chat.
 */
export function useMessages(chatId: string | null, limit = 100) {
  return useQuery({
    queryKey: chatKeys.messages(chatId!),
    queryFn: () => chatService.getMessages(chatId!, limit),
    enabled: !!chatId,
  })
}

// ===== HOOKS MUTATIONS =====

/**
 * Hook pour créer un nouveau chat.
 */
export function useCreateChat() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: ChatCreate) => chatService.createChat(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: chatKeys.all })
      toast.success('Chat créé avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour supprimer un chat.
 */
export function useDeleteChat() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => chatService.deleteChat(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: chatKeys.all })
      toast.success('Chat supprimé')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour envoyer un message (non-streaming).
 */
export function useSendMessage(chatId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: MessageCreate) => {
      if (!chatId) throw new Error('Chat ID required')
      return chatService.sendMessage(chatId, dto)
    },
    onSuccess: () => {
      if (chatId) {
        queryClient.invalidateQueries({ queryKey: chatKeys.messages(chatId) })
      }
      toast.success('Message envoyé')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

// ===== HOOK STREAMING (custom) =====

/**
 * Hook pour streamer un message avec SSE.
 *
 * Gère l'état de streaming, le message en cours de construction,
 * et les sources reçues.
 *
 * @param chatId - ID du chat (null si pas encore de chat actif)
 * @returns { streamMessage, stopStream, isStreaming, currentMessage, sources }
 */
export function useStreamMessage(chatId: string | null) {
  const queryClient = useQueryClient()
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState('')
  const [sources, setSources] = useState<Source[]>([])
  const [pendingValidation, setPendingValidation] = useState<string | null>(null)

  const streamMessage = useCallback(
    async (
      message: string,
      model?: string,
      agentId?: string,
      onValidationRequired?: (validationId: string) => void
    ) => {
      if (!chatId) {
        toast.error('Aucun chat actif')
        return
      }

      setIsStreaming(true)
      setStreamingMessage('')
      setSources([])
      setPendingValidation(null)

      try {
        await chatService.streamMessage(chatId, { message, model, agent_id: agentId }, {
          onChunk: (content) => {
            setStreamingMessage((prev) => prev + content)
          },
          onSources: (newSources) => {
            setSources(newSources)
          },
          onValidationRequired: (validationId) => {
            setPendingValidation(validationId)
            onValidationRequired?.(validationId)
            // Reset le buffer de streaming car le segment a été sauvegardé en DB
            setStreamingMessage('')
            // Invalider immédiatement pour afficher le message tool_call créé en DB
            queryClient.invalidateQueries({
              queryKey: chatKeys.messages(chatId),
            })
          },
          onRefetchMessages: () => {
            // Invalider immédiatement pour afficher les nouveaux messages tool_call
            queryClient.invalidateQueries({
              queryKey: chatKeys.messages(chatId),
            })
          },
          onError: (error) => {
            toast.error(error)
            setIsStreaming(false)
            setPendingValidation(null)
          },
          onDone: () => {
            setIsStreaming(false)
            setPendingValidation(null)
            setStreamingMessage('')
            // Invalider les messages pour refetch
            queryClient.invalidateQueries({
              queryKey: chatKeys.messages(chatId),
            })
            // Invalider la liste des chats pour mettre à jour le titre
            queryClient.invalidateQueries({
              queryKey: chatKeys.lists(),
            })
          },
        })
      } catch (error: any) {
        setIsStreaming(false)
        setPendingValidation(null)

        // Re-throw l'erreur 409 pour que l'appelant puisse la gérer (modale de confirmation)
        const isConflict = error.response?.status === 409 || error.message?.includes('409')
        if (isConflict) {
          throw error
        }

        // Autres erreurs → toast
        toast.error(error.message || 'Erreur lors du streaming')
      }
    },
    [chatId, queryClient]
  )

  const stopStream = useCallback(async () => {
    if (!chatId) return

    try {
      // Le segment partiel sera sauvegardé automatiquement par le backend
      await chatService.stopStream(chatId)
      setIsStreaming(false)
      setPendingValidation(null)
      toast.info('Stream arrêté')

      // Invalider pour afficher le message partiel sauvegardé
      queryClient.invalidateQueries({
        queryKey: chatKeys.messages(chatId),
      })
    } catch (error: any) {
      toast.error('Erreur lors de l\'arrêt du stream')
    }
  }, [chatId, queryClient])

  return {
    streamMessage,
    stopStream,
    isStreaming,
    streamingMessage,
    sources,
    pendingValidation,
  }
}
