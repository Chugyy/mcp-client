"use client"

import { Edit, Trash2, Package, Shield } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { ResourceWithUploads } from "@/lib/api"
import { getStatusBadge, formatDateTime } from "@/lib/resource-utils"
import { UploadList } from "./upload-list"
import { EntityCard } from "@/components/ui/entity-card"
import { cn } from "@/lib/utils"

interface ResourceCardProps {
  resource: ResourceWithUploads
  onEdit?: (id: string) => void
  onDelete?: (id: string) => void
}

export function ResourceCard({
  resource,
  onEdit,
  onDelete,
}: ResourceCardProps) {
  const statusConfig = getStatusBadge(resource.status)
  const isProcessing = resource.status === "pending" || resource.status === "processing"

  return (
    <EntityCard
      icon={Package}
      title={resource.name}
      description={resource.description || "Aucune description"}
      descriptionLines={2}

      actions={[
        {
          icon: Edit,
          onClick: () => onEdit?.(resource.id),
          title: "Modifier la ressource"
        },
        {
          icon: Trash2,
          onClick: () => onDelete?.(resource.id),
          title: "Supprimer la ressource",
          variant: 'ghost',
          className: "text-destructive hover:text-destructive"
        }
      ]}

      afterDescription={
        <UploadList uploads={resource.uploads} maxDisplay={3} compact />
      }

      isSystem={resource.is_system}
      badges={
        <>
          <Badge
            variant={statusConfig.variant}
            className={cn("text-xs flex-shrink-0", statusConfig.className)}
          >
            {statusConfig.label}
          </Badge>

          {resource.status === 'ready' && resource.chunk_count > 0 && (
            <Badge variant="outline" className="text-xs flex-shrink-0">
              {resource.chunk_count} chunks
            </Badge>
          )}

          {resource.status === 'ready' && resource.indexed_at && (
            <Badge variant="outline" className="text-xs flex-shrink-0">
              Indexé le {formatDateTime(resource.indexed_at)}
            </Badge>
          )}

          {resource.status === 'error' && resource.error_message && (
            <Badge variant="destructive" className="text-xs flex-shrink-0 max-w-[200px] truncate" title={resource.error_message}>
              {resource.error_message}
            </Badge>
          )}
        </>
      }

      overlay={isProcessing ? {
        show: true,
        message: resource.status === "pending" ? "Préparation..." : "Ingestion en cours..."
      } : undefined}
    />
  )
}
