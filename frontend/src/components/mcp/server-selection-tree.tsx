"use client"

import { TypeIcon } from "./type-icon"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import type { MCPServerType } from "@/services/mcp/mcp.types"

interface ParsedServer {
  id: string
  name: string
  type: MCPServerType
  args?: string[]
  env?: Record<string, string>
}

interface ServerSelectionTreeProps {
  servers: ParsedServer[]
  selectedIds: string[]
  onToggle: (id: string, selected: boolean) => void
}

export function ServerSelectionTree({ servers, selectedIds, onToggle }: ServerSelectionTreeProps) {
  const isSelected = (id: string) => selectedIds.includes(id)

  return (
    <div className="border rounded-lg divide-y max-h-[400px] overflow-y-auto">
      {servers.map((server) => (
        <div
          key={server.id}
          className="flex items-center gap-3 p-3 hover:bg-muted/50 transition-colors"
        >
          <Checkbox
            checked={isSelected(server.id)}
            onCheckedChange={(checked) => onToggle(server.id, checked === true)}
          />
          <TypeIcon type={server.type} size={20} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium truncate">{server.name}</span>
              <Badge variant="outline" className="text-xs">
                {server.type.toUpperCase()}
              </Badge>
            </div>
            {server.args && server.args.length > 0 && (
              <p className="text-xs text-muted-foreground truncate mt-0.5">
                {server.args.join(" ")}
              </p>
            )}
          </div>
          <div className="flex flex-col items-end text-xs text-muted-foreground">
            {server.args && (
              <span>{server.args.length} arg{server.args.length > 1 ? "s" : ""}</span>
            )}
            {server.env && Object.keys(server.env).length > 0 && (
              <span>{Object.keys(server.env).length} var{Object.keys(server.env).length > 1 ? "s" : ""}</span>
            )}
          </div>
        </div>
      ))}

      {servers.length === 0 && (
        <div className="p-8 text-center text-sm text-muted-foreground">
          Aucun serveur détecté
        </div>
      )}
    </div>
  )
}
