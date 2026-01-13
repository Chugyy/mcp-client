"use client"

import { LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { AuthenticatedImage } from '@/components/ui/authenticated-image'
import { cn } from '@/lib/utils'

export interface EntityCardAction {
  icon: LucideIcon
  onClick: () => void
  title: string
  variant?: 'default' | 'ghost' | 'destructive'
  disabled?: boolean
  className?: string
}

export interface EntityCardProps {
  // === HEADER ===
  icon: LucideIcon | string // Icon component, public URL, or upload_id
  title: string

  // === TOGGLE ===
  enableToggle?: boolean
  toggleValue?: boolean
  onToggle?: (checked: boolean) => void
  toggleDisabled?: boolean

  // === ACTIONS ===
  actions?: EntityCardAction[]

  // === BODY SLOTS ===
  description?: string
  descriptionLines?: 2 | 3
  beforeDescription?: React.ReactNode
  afterDescription?: React.ReactNode

  // === FOOTER ===
  badges?: React.ReactNode
  isSystem?: boolean

  // === OVERLAY (Resources) ===
  overlay?: {
    show: boolean
    icon?: React.ReactNode
    message: string
  }

  // === STYLING ===
  className?: string
  contentClassName?: string
  disabled?: boolean

  // === CLICK HANDLER ===
  onClick?: () => void
}

export function EntityCard({
  icon,
  title,
  enableToggle = false,
  toggleValue = false,
  onToggle,
  toggleDisabled = false,
  actions = [],
  description,
  descriptionLines = 3,
  beforeDescription,
  afterDescription,
  badges,
  isSystem = false,
  overlay,
  className,
  contentClassName,
  disabled = false,
  onClick,
}: EntityCardProps) {
  const IconComponent = typeof icon === 'string' ? null : icon
  const iconValue = typeof icon === 'string' ? icon : null

  // Detect if iconValue is a UUID (upload_id) or a public URL
  const isUploadId = iconValue && !iconValue.startsWith('http://') && !iconValue.startsWith('https://') && !iconValue.startsWith('/')
  const publicUrl = iconValue && !isUploadId ? iconValue : null

  const isProcessing = overlay?.show || false

  return (
    <Card
      className={cn(
        "relative hover:border-primary/50 transition-colors flex flex-col !p-0 !gap-0 h-full",
        onClick && "cursor-pointer",
        className
      )}
      onClick={onClick}
    >
      {/* Overlay pour processing */}
      {overlay?.show && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center rounded-lg z-10">
          <div className="flex flex-col items-center gap-2">
            {overlay.icon || (
              <div className="size-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            )}
            <p className="text-sm font-medium">{overlay.message}</p>
          </div>
        </div>
      )}

      <div className={cn("flex flex-col flex-1", isProcessing && "pointer-events-none opacity-50", contentClassName)}>
        {/* Header: Icône + Nom + Boutons */}
        <CardHeader className="px-3 pt-3 pb-2">
          <div className="flex items-center gap-2 min-w-0">
            {/* Icône/Avatar */}
            <div className="size-8 rounded-full border bg-muted flex items-center justify-center overflow-hidden flex-shrink-0">
              {isUploadId ? (
                <AuthenticatedImage
                  uploadId={iconValue}
                  alt={title}
                  className="size-full object-cover"
                  loadingClassName="size-8 flex items-center justify-center"
                />
              ) : publicUrl ? (
                <img src={publicUrl} alt={title} className="size-full object-cover" />
              ) : IconComponent ? (
                <IconComponent className="size-4 text-muted-foreground" />
              ) : null}
            </div>

            {/* Nom tronqué */}
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-sm truncate">{title}</h3>
            </div>

            {/* Boutons d'action */}
            <div className="flex gap-0.5 flex-shrink-0 items-center" onClick={(e) => e.stopPropagation()}>
              {/* Toggle Switch */}
              {enableToggle && (
                <Switch
                  checked={toggleValue}
                  onCheckedChange={onToggle}
                  disabled={toggleDisabled || disabled}
                  className="data-[state=unchecked]:border-input data-[state=unchecked]:bg-transparent [&_span]:transition-all data-[state=unchecked]:[&_span]:size-3 data-[state=unchecked]:[&_span]:translate-x-0.5 data-[state=unchecked]:[&_span]:bg-input data-[state=unchecked]:[&_span]:shadow-none data-[state=unchecked]:[&_span]:rtl:-translate-x-0.5 scale-75"
                />
              )}

              {/* Action buttons */}
              {actions.map((action, idx) => {
                const ActionIcon = action.icon
                return (
                  <Button
                    key={idx}
                    size="icon"
                    variant={action.variant || 'ghost'}
                    className={cn(
                      "size-7",
                      action.variant === 'destructive' && "text-destructive hover:text-destructive",
                      action.className
                    )}
                    onClick={action.onClick}
                    disabled={action.disabled || disabled}
                    title={action.title}
                  >
                    <ActionIcon className="size-3.5" />
                    <span className="sr-only">{action.title}</span>
                  </Button>
                )
              })}
            </div>
          </div>
        </CardHeader>

        {/* Before Description slot */}
        {beforeDescription && (
          <CardContent className="px-3 py-0 pb-1">
            {beforeDescription}
          </CardContent>
        )}

        {/* Description */}
        {description && (
          <CardContent className="px-3 py-0 pb-2">
            <p className={cn(
              "text-xs text-muted-foreground",
              descriptionLines === 2 ? "line-clamp-2" : "line-clamp-3"
            )}>
              {description}
            </p>
          </CardContent>
        )}

        {/* After Description slot */}
        {afterDescription && (
          <CardContent className="px-3 py-0 pb-2">
            {afterDescription}
          </CardContent>
        )}

        {/* Footer avec badges */}
        {(isSystem || badges) && (
          <CardContent className="px-3 pb-3 pt-2 mt-auto">
            <div className="flex gap-1 flex-wrap">
              {isSystem && (
                <Badge
                  variant="secondary"
                  className="text-xs flex-shrink-0 bg-blue-500/10 text-blue-700 border-blue-500/20 dark:bg-blue-500/20 dark:text-blue-400"
                >
                  System
                </Badge>
              )}
              {badges}
            </div>
          </CardContent>
        )}
      </div>
    </Card>
  )
}
