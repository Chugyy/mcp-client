"use client"

import { useQuery } from '@tanstack/react-query'
import { uploadsService } from './uploads.service'

/**
 * Query keys for uploads
 */
export const uploadKeys = {
  all: ['uploads'] as const,
  detail: (id: string) => [...uploadKeys.all, 'detail', id] as const,
  blob: (id: string) => [...uploadKeys.all, 'blob', id] as const,
}

/**
 * Hook to fetch an upload and create a blob URL
 * Useful for displaying images with authentication
 * The blob URL is cached by React Query
 */
export function useUploadBlobUrl(uploadId: string | null | undefined, enabled: boolean = true) {
  return useQuery({
    queryKey: uploadKeys.blob(uploadId || ''),
    queryFn: () => uploadsService.getUploadBlobUrl(uploadId!),
    enabled: !!uploadId && enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes - images rarely change
    gcTime: 30 * 60 * 1000, // 30 minutes cache
  })
}
