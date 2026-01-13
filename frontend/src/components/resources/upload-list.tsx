"use client"

import { getFileIcon } from "@/lib/file-utils"
import { formatBytes } from "@/hooks/use-file-upload"

export interface Upload {
  id: string
  resource_id: string | null
  filename: string
  file_path: string
  file_size: number
  mime_type: string
  type: 'avatar' | 'document' | 'resource'
  created_at: string
}

interface UploadListProps {
  uploads: Upload[]
  maxDisplay?: number
  compact?: boolean
}

export function UploadList({ uploads, maxDisplay = 3, compact = false }: UploadListProps) {
  if (uploads.length === 0) {
    return (
      <p className="text-xs text-muted-foreground italic">
        Aucun fichier
      </p>
    )
  }

  const displayedUploads = maxDisplay > 0 ? uploads.slice(0, maxDisplay) : uploads
  const remainingCount = maxDisplay > 0 ? uploads.length - maxDisplay : 0

  return (
    <div className={compact ? "space-y-0.5" : "space-y-1"}>
      {displayedUploads.map((upload) => {
        const Icon = getFileIcon(upload.mime_type, upload.filename)
        return (
          <div
            key={upload.id}
            className={`flex items-center gap-2 ${compact ? 'text-[11px]' : 'text-xs'}`}
          >
            <Icon className={`${compact ? 'size-3' : 'size-3.5'} text-muted-foreground flex-shrink-0`} />
            <span className="truncate flex-1">{upload.filename}</span>
            <span className="text-muted-foreground flex-shrink-0">
              ({formatBytes(upload.file_size)})
            </span>
          </div>
        )
      })}
      {remainingCount > 0 && (
        <p className={`${compact ? 'text-[11px]' : 'text-xs'} text-muted-foreground pl-5`}>
          + {remainingCount} autre{remainingCount > 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}
