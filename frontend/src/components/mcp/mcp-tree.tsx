"use client"

import React, { useState } from "react"
import { Server, Wrench, ChevronRight, ChevronDown } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip"
import type { MCPServerWithTools } from "@/services/mcp/mcp.types"

interface MCPTreeProps {
  servers: MCPServerWithTools[]
  onToggleServer: (serverId: string, enabled: boolean) => void
  onToggleTool: (serverId: string, toolId: string, enabled: boolean) => void
  checkedServers: string[]
  checkedTools: string[]
}

export function MCPTree({
  servers,
  onToggleServer,
  onToggleTool,
  checkedServers,
  checkedTools
}: MCPTreeProps) {
  const [expandedServers, setExpandedServers] = useState<Set<string>>(
    new Set(checkedServers)
  )

  const toggleExpand = (serverId: string) => {
    setExpandedServers(prev => {
      const next = new Set(prev)
      if (next.has(serverId)) {
        next.delete(serverId)
      } else {
        next.add(serverId)
      }
      return next
    })
  }

  const isServerChecked = (serverId: string) => checkedServers.includes(serverId)
  const isToolChecked = (toolId: string) => checkedTools.includes(toolId)

  const getServerCheckState = (server: MCPServer): boolean | "indeterminate" => {
    const isServerEnabled = isServerChecked(server.id)
    if (!isServerEnabled) return false

    const enabledToolsCount = server.tools.filter(t => isToolChecked(t.id)).length
    if (enabledToolsCount === 0) return false
    if (enabledToolsCount === server.tools.length) return true
    return "indeterminate"
  }

  return (
    <div className="space-y-1">
      {servers.map((server) => {
        const isExpanded = expandedServers.has(server.id)
        const checkState = getServerCheckState(server)

        return (
          <div key={server.id} className="space-y-0.5">
            <div className="flex items-center gap-2 p-2">
              <button
                type="button"
                onClick={() => toggleExpand(server.id)}
                className="p-0.5"
              >
                {isExpanded ? (
                  <ChevronDown className="size-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="size-4 text-muted-foreground" />
                )}
              </button>
              <Checkbox
                checked={checkState}
                onCheckedChange={(checked) => onToggleServer(server.id, checked === true)}
              />
              <Server className="size-4 text-muted-foreground" />
              <span className="flex-1 text-sm font-medium">{server.name}</span>
              <span className="text-xs text-muted-foreground">
                {server.tools.length} outils
              </span>
            </div>

            {isExpanded && server.tools.length > 0 && (
              <div className="ml-6 space-y-0.5 pl-3">
                {server.tools.map((tool) => (
                  <div
                    key={tool.id}
                    className="flex items-center gap-2 p-2"
                  >
                    <Checkbox
                      checked={isToolChecked(tool.id)}
                      onCheckedChange={(checked) =>
                        onToggleTool(server.id, tool.id, checked === true)
                      }
                      disabled={!isServerChecked(server.id)}
                    />
                    <Wrench className="size-4 text-muted-foreground" />
                    <span className="flex-1 text-sm">{tool.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}

      {servers.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-4">
          Aucun serveur MCP disponible
        </p>
      )}
    </div>
  )
}
