"use client"

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Validation } from "@/services/validations/validations.types"
import { Check, X, MessageSquare } from "lucide-react"
import { cn } from "@/lib/utils"

interface ArchivesSidebarProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  items: Validation[]
  onItemClick?: (id: string) => void
}

export function ArchivesSidebar({
  open,
  onOpenChange,
  items,
  onItemClick,
}: ArchivesSidebarProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <Check className="size-4 text-green-600" />
      case 'rejected':
        return <X className="size-4 text-red-600" />
      case 'feedback':
        return <MessageSquare className="size-4 text-blue-600" />
      default:
        return null
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'approved':
        return 'Validé'
      case 'rejected':
        return 'Annulé'
      case 'feedback':
        return 'Feedback'
      default:
        return status
    }
  }

  const getStatusVariant = (status: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (status) {
      case 'approved':
        return 'default'
      case 'rejected':
        return 'destructive'
      case 'feedback':
        return 'outline'
      default:
        return 'outline'
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Archives</SheetTitle>
          <SheetDescription>
            Historique des validations traitées
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-8rem)] mt-6">
          <div className="space-y-4 px-4">
            {items.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                Aucun élément archivé
              </p>
            ) : (
              items.map((item) => (
                <div
                  key={item.id}
                  className="border rounded-lg p-4 space-y-3 hover:bg-accent/50 transition-colors cursor-pointer"
                  onClick={() => onItemClick?.(item.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="font-semibold text-sm leading-tight flex-1">
                      {item.title}
                    </h4>
                    <div className="flex items-center gap-1">
                      {getStatusIcon(item.status)}
                    </div>
                  </div>

                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {item.description}
                  </p>

                  <div className="flex flex-wrap gap-1.5">
                    <Badge variant="outline" className="text-xs">
                      {item.source}
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      {item.process}
                    </Badge>
                    {item.agent_id && (
                      <Badge variant="default" className="text-xs">
                        {item.agent_id}
                      </Badge>
                    )}
                    <Badge
                      variant={getStatusVariant(item.status)}
                      className={cn(
                        "text-xs",
                        item.status === 'feedback' && "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/30 dark:text-blue-400 dark:border-blue-800"
                      )}
                    >
                      {getStatusLabel(item.status)}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                    <span>{item.user_id}</span>
                    <span>{formatDate(item.created_at)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
