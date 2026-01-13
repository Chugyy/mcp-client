"use client"

import { Badge } from '@/components/ui/badge'
import { FileText, Play, Pause, Archive } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AutomationStatusBadgeProps {
  status: 'draft' | 'active' | 'paused' | 'archived'
  className?: string
}

export function AutomationStatusBadge({ status, className }: AutomationStatusBadgeProps) {
  const config = {
    draft: {
      label: 'BROUILLON',
      icon: FileText,
      className: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    },
    active: {
      label: 'ACTIVE',
      icon: Play,
      className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    },
    paused: {
      label: 'PAUSE',
      icon: Pause,
      className: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    },
    archived: {
      label: 'ARCHIVÉE',
      icon: Archive,
      className: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    },
  }

  const { label, icon: Icon, className: statusClassName } = config[status]

  return (
    <Badge variant="outline" className={cn(statusClassName, 'flex items-center gap-1', className)}>
      <Icon className="size-3" />
      {label}
    </Badge>
  )
}
