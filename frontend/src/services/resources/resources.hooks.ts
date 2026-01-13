"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { resourceService, resourceKeys } from './resources.service'
import { extractErrorMessage } from '@/lib/error-handler'
import type {
  CreateResourceDTO,
  UpdateResourceDTO,
  Resource,
  Upload
} from './resources.types'

/**
 * Hook pour lister toutes les ressources (avec options)
 * Polling automatique si au moins une ressource est en cours d'ingestion
 */
export function useResources(params?: { enabled_only?: boolean }) {
  return useQuery({
    queryKey: resourceKeys.list(params),
    queryFn: () => resourceService.getAll(params),
    refetchInterval: (query) => {
      // Si au moins une ressource est en "pending" ou "processing", refetch toutes les 3 secondes
      const hasProcessing = query.state.data?.some((r: Resource) =>
        r.status === "pending" || r.status === "processing"
      )
      return hasProcessing ? 3000 : false
    }
  })
}

/**
 * Hook pour récupérer une ressource spécifique
 */
export function useResource(id: string) {
  return useQuery({
    queryKey: resourceKeys.detail(id),
    queryFn: () => resourceService.getById(id),
    enabled: !!id,
  })
}

/**
 * Hook pour lister les uploads d'une ressource
 */
export function useResourceUploads(resourceId: string) {
  return useQuery({
    queryKey: resourceKeys.uploads(resourceId),
    queryFn: () => resourceService.getUploads(resourceId),
    enabled: !!resourceId,
  })
}

/**
 * Hook pour créer une nouvelle ressource
 */
export function useCreateResource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: CreateResourceDTO) => resourceService.create(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: resourceKeys.all })
      toast.success('Ressource créée avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour mettre à jour une ressource
 */
export function useUpdateResource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateResourceDTO }) =>
      resourceService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: resourceKeys.all })
      toast.success('Ressource mise à jour avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour supprimer une ressource
 */
export function useDeleteResource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: string | { id: string; headers?: Record<string, string> }) => {
      // Support ancien format (string) et nouveau format (objet)
      if (typeof params === 'string') {
        return resourceService.delete(params)
      }
      return resourceService.delete(params.id, params.headers)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: resourceKeys.all })
      toast.success('Ressource supprimée avec succès')
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
 * Hook pour déclencher l'ingestion d'une ressource
 */
export function useIngestResource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (resourceId: string) => resourceService.ingest(resourceId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: resourceKeys.all })
      toast.success(data.message || 'Ingestion déclenchée avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour uploader un fichier vers une ressource
 */
export function useUploadFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ resourceId, file }: { resourceId: string; file: File }) =>
      resourceService.uploadFile(resourceId, file),
    onSuccess: (_, { resourceId }) => {
      queryClient.invalidateQueries({ queryKey: resourceKeys.uploads(resourceId) })
      queryClient.invalidateQueries({ queryKey: resourceKeys.detail(resourceId) })
      toast.success('Fichier uploadé avec succès')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}

/**
 * Hook pour supprimer un upload
 */
export function useDeleteUpload() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (uploadId: string) => resourceService.deleteUpload(uploadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: resourceKeys.all })
      toast.success('Fichier supprimé')
    },
    onError: (error: any) => {
      toast.error(extractErrorMessage(error))
    },
  })
}
