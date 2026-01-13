"use client"

import { useUploadBlobUrl } from '@/services/uploads/uploads.hooks'
import { Loader2 } from 'lucide-react'
import { ImgHTMLAttributes, useEffect } from 'react'

interface AuthenticatedImageProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  uploadId: string | null | undefined
  fallback?: string
  loadingClassName?: string
}

/**
 * Component for displaying images that require authentication
 * Fetches the image via authenticated endpoint and creates a blob URL
 */
export function AuthenticatedImage({
  uploadId,
  fallback,
  alt,
  className,
  loadingClassName,
  ...props
}: AuthenticatedImageProps) {
  const { data: blobUrl, isLoading, error } = useUploadBlobUrl(uploadId)

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl)
      }
    }
  }, [blobUrl])

  if (isLoading) {
    return (
      <div className={loadingClassName || className}>
        <Loader2 className="animate-spin" />
      </div>
    )
  }

  if (error || !blobUrl) {
    if (fallback) {
      return <img src={fallback} alt={alt} className={className} {...props} />
    }
    return null
  }

  return <img src={blobUrl} alt={alt} className={className} {...props} />
}
