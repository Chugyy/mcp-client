"use client"

import Image from "next/image"
import { cn } from "@/lib/utils"
import type { MCPServerType } from "@/services/mcp/mcp.types"

interface TypeIconProps {
  type: MCPServerType
  className?: string
  size?: number
}

// URLs Icons8 pour chaque type
const ICON_URLS: Record<MCPServerType, string> = {
  http: "https://img.icons8.com/?id=115033&format=png",
  npx: "https://img.icons8.com/?id=24895&format=png",
  uvx: "https://img.icons8.com/?id=101379&format=png",
  docker: "https://img.icons8.com/?id=60038&format=png",
}

export function TypeIcon({ type, className, size = 24 }: TypeIconProps) {
  const url = ICON_URLS[type]

  if (!url) {
    return null
  }

  return (
    <Image
      src={`${url}&size=${size}`}
      alt={`${type} icon`}
      width={size}
      height={size}
      className={cn("flex-shrink-0", className)}
    />
  )
}
