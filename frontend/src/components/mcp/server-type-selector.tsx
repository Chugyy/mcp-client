"use client"

import { TypeIcon } from "./type-icon"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { MCPServerType } from "@/services/mcp/mcp.types"
import { SERVER_TYPES } from "@/services/mcp/mcp.constants"

interface ServerTypeSelectorProps {
  value: MCPServerType
  onChange: (type: MCPServerType) => void
  className?: string
}

export function ServerTypeSelector({ value, onChange, className }: ServerTypeSelectorProps) {
  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-4 gap-3", className)}>
      {(Object.entries(SERVER_TYPES) as [MCPServerType, typeof SERVER_TYPES[MCPServerType]][]).map(([key, config]) => {
        const isSelected = value === key

        return (
          <button
            key={key}
            type="button"
            onClick={() => onChange(key)}
            className={cn(
              "relative flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all hover:shadow-md",
              isSelected
                ? "border-primary bg-primary/5 shadow-sm"
                : "border-muted hover:border-muted-foreground/20"
            )}
          >
            <TypeIcon type={key} size={32} />
            <div className="flex flex-col items-center gap-1">
              <span className="text-sm font-medium">{config.label}</span>
              {config.autoInstall && (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                  Auto-install
                </Badge>
              )}
            </div>
            {isSelected && (
              <div className="absolute top-2 right-2 size-2 rounded-full bg-primary" />
            )}
          </button>
        )
      })}
    </div>
  )
}
