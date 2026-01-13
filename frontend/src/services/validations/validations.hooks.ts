"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { validationService, validationKeys } from './validations.service'
import { extractErrorMessage } from '@/lib/error-handler'
import type {
  ValidationCreate,
  ValidationUpdate,
  ApproveValidationRequest,
  RejectValidationRequest,
  FeedbackValidationRequest,
} from './validations.types'

// Ré-exporter validationKeys pour utilisation dans les composants
export { validationKeys }

// ===== HOOKS GET (useQuery) =====

/**
 * Hook pour récupérer la liste des validations (avec filtre optionnel par statut).
 * Auto-refresh toutes les 1s si des validations sont pending.
 */
export function useValidations(status?: string) {
  return useQuery({
    queryKey: status ? validationKeys.filtered(status) : validationKeys.lists(),
    queryFn: () => validationService.getAll(status),
    refetchInterval: (query) => {
      const data = query.state.data as any[]
      const hasPending = data?.some((v: any) => v.status === "pending")
      return status === 'pending' || hasPending ? 1000 : false
    }
  })
}

/**
 * Hook pour récupérer une validation par ID.
 */
export function useValidation(id: string | null) {
  return useQuery({
    queryKey: validationKeys.detail(id!),
    queryFn: () => validationService.getById(id!),
    enabled: !!id,
  })
}

/**
 * Hook pour récupérer les logs d'action d'une validation.
 */
export function useValidationLogs(id: string | null) {
  return useQuery({
    queryKey: validationKeys.logs(id!),
    queryFn: () => validationService.getLogs(id!),
    enabled: !!id,
  })
}

// ===== HOOKS MUTATIONS =====

/**
 * Hook pour créer une nouvelle validation.
 */
export function useCreateValidation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: ValidationCreate) => validationService.create(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: validationKeys.all })
      toast.success('Validation créée avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour mettre à jour le statut d'une validation.
 */
export function useUpdateValidationStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: ValidationUpdate }) =>
      validationService.updateStatus(id, dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: validationKeys.all })
      toast.success('Statut mis à jour')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour approuver une validation.
 */
export function useApproveValidation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: ApproveValidationRequest }) =>
      validationService.approve(id, request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: validationKeys.all })

      // Phase 5: Invalider aussi les messages du chat si la validation est liée à un chat
      queryClient.invalidateQueries({ queryKey: ['chats'] })

      toast.success(data.message || 'Validation approuvée')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour rejeter une validation.
 */
export function useRejectValidation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: RejectValidationRequest }) =>
      validationService.reject(id, request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: validationKeys.all })

      // Phase 5: Invalider aussi les chats
      queryClient.invalidateQueries({ queryKey: ['chats'] })

      toast.success(data.message || 'Validation rejetée')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour donner un feedback sur une validation.
 */
export function useFeedbackValidation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: FeedbackValidationRequest }) =>
      validationService.feedback(id, request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: validationKeys.all })
      toast.success(data.message || 'Feedback envoyé')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}
