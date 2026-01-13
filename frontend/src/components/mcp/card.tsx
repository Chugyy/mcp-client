"use client"

import { Server, Edit, Copy, Trash2, RefreshCw, CheckCircle2, XCircle, AlertCircle, Clock, Key } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { EntityCard } from "@/components/ui/entity-card"
import { TypeIcon } from "./type-icon"
import type { MCPServerType } from "@/services/mcp/mcp.types"
import { SERVER_TYPES } from "@/services/mcp/mcp.constants"

interface MCPCardProps {
  id: string
  name: string
  description?: string
  type: MCPServerType
  url?: string
  args?: string[]
  authType?: "api-key" | "oauth" | "none"
  status: "pending" | "pending_authorization" | "active" | "failed" | "unreachable"
  statusMessage?: string
  stale?: boolean
  enabled?: boolean
  isSystem?: boolean
  onEdit?: (id: string) => void
  onDelete?: (id: string) => void
  onDuplicate?: (id: string) => void
  onToggle?: (id: string, enabled: boolean) => void
  onSync: (id: string) => void
}

export function MCPCard({
  id,
  name,
  description,
  type,
  url,
  args,
  authType,
  status,
  statusMessage,
  stale = false,
  enabled = true,
  isSystem = false,
  onEdit,
  onDelete,
  onDuplicate,
  onToggle,
  onSync
}: MCPCardProps) {
  const typeConfig = SERVER_TYPES[type]

  // Generate display text based on type
  const displayText = type === 'http'
    ? url || 'No URL'
    : args?.join(' ') || 'No args'

  return (
    <EntityCard
      icon={Server}
      title={name}
      description={description || "Aucune description"}
      descriptionLines={2}

      beforeDescription={
        <p className="text-xs text-muted-foreground truncate" title={displayText}>
          {displayText}
        </p>
      }

      enableToggle
      toggleValue={enabled}
      onToggle={(checked) => onToggle?.(id, checked)}

      actions={[
        {
          icon: RefreshCw,
          onClick: () => onSync(id),
          title: "Synchroniser le serveur MCP"
        },
        {
          icon: Copy,
          onClick: () => onDuplicate?.(id),
          title: "Dupliquer le serveur MCP"
        },
        {
          icon: Edit,
          onClick: () => onEdit?.(id),
          title: "Modifier le serveur MCP"
        },
        {
          icon: Trash2,
          onClick: () => onDelete?.(id),
          title: "Supprimer le serveur MCP",
          variant: 'ghost',
          className: "text-destructive hover:text-destructive"
        }
      ]}

      isSystem={isSystem}
      badges={
        <>
          {/* Type Badge */}
          <Badge variant="outline" className={`text-xs flex-shrink-0 ${typeConfig.badgeColor}`} title={typeConfig.description}>
            <TypeIcon type={type} size={14} className="mr-1" />
            {typeConfig.label}
          </Badge>

          {/* Auth Badge for HTTP servers */}
          {type === 'http' && authType && (
            <Badge variant="outline" className="text-xs flex-shrink-0">
              {authType === "api-key" ? "Clé API" : authType === "oauth" ? "OAuth" : "Sans Auth"}
            </Badge>
          )}

          {/* Auto-install badge for stdio servers */}
          {type !== 'http' && typeConfig.autoInstall && (
            <Badge variant="secondary" className="text-xs flex-shrink-0">
              Auto-install
            </Badge>
          )}

          {/* Status Badges */}
          {status === "active" && (
            <Badge
              variant="outline"
              className="text-xs flex-shrink-0 bg-green-500/10 text-green-700 border-green-500/20 dark:bg-green-500/20 dark:text-green-400"
              title={statusMessage || "Serveur actif et opérationnel"}
            >
              <CheckCircle2 className="size-3 mr-1" />
              Active
            </Badge>
          )}
          {status === "unreachable" && (
            <Badge
              variant="outline"
              className="text-xs flex-shrink-0 bg-red-500/10 text-red-700 border-red-500/20 dark:bg-red-500/20 dark:text-red-400"
              title={statusMessage || "Serveur injoignable"}
            >
              <AlertCircle className="size-3 mr-1" />
              Unreachable
            </Badge>
          )}
          {status === "failed" && (
            <Badge
              variant="outline"
              className="text-xs flex-shrink-0 bg-red-500/10 text-red-700 border-red-500/20 dark:bg-red-500/20 dark:text-red-400"
              title={statusMessage || "Erreur d'authentification"}
            >
              <XCircle className="size-3 mr-1" />
              Failed
            </Badge>
          )}
          {status === "pending" && (
            <Badge
              variant="outline"
              className="text-xs flex-shrink-0 bg-gray-500/10 text-gray-700 border-gray-500/20 dark:bg-gray-500/20 dark:text-gray-400"
              title={statusMessage || "En attente de vérification"}
            >
              <Clock className="size-3 mr-1" />
              Pending
            </Badge>
          )}
          {status === "pending_authorization" && (
            <Badge
              variant="outline"
              className="text-xs flex-shrink-0 bg-yellow-500/10 text-yellow-700 border-yellow-500/20 dark:bg-yellow-500/20 dark:text-yellow-400"
              title={statusMessage || "Autorisation OAuth requise"}
            >
              <Key className="size-3 mr-1" />
              Pending OAuth
            </Badge>
          )}
          {stale && (
            <Badge variant="outline" className="text-xs flex-shrink-0 bg-orange-500/10 text-orange-700 border-orange-500/20 dark:bg-orange-500/20 dark:text-orange-400">
              Needs Sync
            </Badge>
          )}
        </>
      }
    />
  )
}
