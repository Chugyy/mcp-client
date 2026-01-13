"use client"

import { Users, Edit, Copy, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"

interface TeamCardProps {
  id: string
  name: string
  description?: string
  tags?: string[]
  agentCount: number
  enabled?: boolean
  onEdit?: (id: string) => void
  onDelete?: (id: string) => void
  onDuplicate?: (id: string) => void
  onToggle?: (id: string, enabled: boolean) => void
}

export function TeamCard({
  id,
  name,
  description,
  tags = [],
  agentCount,
  enabled = true,
  onEdit,
  onDelete,
  onDuplicate,
  onToggle
}: TeamCardProps) {
  return (
    <Card className="relative hover:border-primary/50 transition-colors flex flex-col !p-0 !gap-0">
      {/* Header: Icône + Nom + Boutons - collé en haut */}
      <CardHeader className="px-3 pt-3 pb-2">
        <div className="flex items-center gap-2 min-w-0">
          {/* Icône */}
          <div className="size-8 rounded-full border bg-muted flex items-center justify-center flex-shrink-0">
            <Users className="size-4 text-muted-foreground" />
          </div>

          {/* Nom tronqué */}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm truncate">
              {name}
            </h3>
          </div>

          {/* Boutons d'action */}
          <div className="flex gap-0.5 flex-shrink-0 items-center">
            <Switch
              id={`toggle-team-${id}`}
              checked={enabled}
              onCheckedChange={(checked) => onToggle?.(id, checked)}
              className="data-[state=unchecked]:border-input data-[state=unchecked]:bg-transparent [&_span]:transition-all data-[state=unchecked]:[&_span]:size-3 data-[state=unchecked]:[&_span]:translate-x-0.5 data-[state=unchecked]:[&_span]:bg-input data-[state=unchecked]:[&_span]:shadow-none data-[state=unchecked]:[&_span]:rtl:-translate-x-0.5 scale-75"
            />
            <Button
              size="icon"
              variant="ghost"
              className="size-7"
              onClick={() => onDuplicate?.(id)}
              title="Duplicate team"
            >
              <Copy className="size-3.5" />
              <span className="sr-only">Duplicate team</span>
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="size-7"
              onClick={() => onEdit?.(id)}
              title="Edit team"
            >
              <Edit className="size-3.5" />
              <span className="sr-only">Edit team</span>
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-destructive hover:text-destructive"
              onClick={() => onDelete?.(id)}
              title="Delete team"
            >
              <Trash2 className="size-3.5" />
              <span className="sr-only">Delete team</span>
            </Button>
          </div>
        </div>
      </CardHeader>

      {/* Description - max 3 lignes */}
      <CardContent className="px-3 py-0 pb-2">
        <p className="text-xs text-muted-foreground line-clamp-3">
          {description || "Aucune description"}
        </p>
      </CardContent>

      {/* Footer avec badges */}
      {(tags.length > 0 || agentCount > 0) && (
        <CardContent className="px-3 pb-3 pt-2">
          <div className="flex gap-1 overflow-hidden">
            <Badge variant="outline" className="text-xs flex-shrink-0">
              {agentCount} {agentCount > 1 ? "agents" : "agent"}
            </Badge>
            {tags.slice(0, 2).map((tag, idx) => (
              <Badge key={idx} variant="secondary" className="text-xs flex-shrink-0">
                {tag}
              </Badge>
            ))}
            {tags.length > 2 && (
              <Badge variant="outline" className="text-xs flex-shrink-0">
                +{tags.length - 2} autre{tags.length - 2 > 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  )
}
