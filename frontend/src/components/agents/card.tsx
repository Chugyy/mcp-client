"use client"

import { Bot, Edit, Copy, Trash2, Shield } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { EntityCard } from "@/components/ui/entity-card"

interface AgentCardProps {
  id: string
  name: string
  description?: string
  avatar?: string // Now this is the upload_id from backend
  tags?: string[]
  enabled?: boolean
  isSystem?: boolean
  onEdit?: (id: string) => void
  onDelete?: (id: string) => void
  onDuplicate?: (id: string) => void
  onToggle?: (id: string, enabled: boolean) => void
}

export function AgentCard({
  id,
  name,
  description,
  avatar,
  tags = [],
  enabled = true,
  isSystem = false,
  onEdit,
  onDelete,
  onDuplicate,
  onToggle
}: AgentCardProps) {
  return (
    <EntityCard
      icon={avatar || Bot}
      title={name}
      description={description || "Aucune description"}
      descriptionLines={3}

      enableToggle
      toggleValue={enabled}
      onToggle={(checked) => onToggle?.(id, checked)}
      toggleDisabled={isSystem}

      actions={[
        {
          icon: Copy,
          onClick: () => onDuplicate?.(id),
          title: "Duplicate agent",
          disabled: isSystem
        },
        {
          icon: Edit,
          onClick: () => onEdit?.(id),
          title: "Edit agent",
          disabled: isSystem
        },
        {
          icon: Trash2,
          onClick: () => onDelete?.(id),
          title: "Delete agent",
          variant: 'ghost',
          className: "text-destructive hover:text-destructive",
          disabled: isSystem
        }
      ]}

      isSystem={isSystem}
      badges={
        <>
          {tags.slice(0, 3).map((tag, idx) => (
            <Badge key={idx} variant="secondary" className="text-xs flex-shrink-0">
              {tag}
            </Badge>
          ))}
          {tags.length > 3 && (
            <Badge variant="outline" className="text-xs flex-shrink-0">
              +{tags.length - 3} autre{tags.length - 3 > 1 ? 's' : ''}
            </Badge>
          )}
        </>
      }
    />
  )
}
