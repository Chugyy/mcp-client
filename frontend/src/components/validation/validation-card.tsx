"use client"

import { Check, X, MessageSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface ValidationCardProps {
  id: string
  title: string
  description: string | null
  source: string
  process: string
  agent_id?: string | null
  user_id: string
  created_at: string
  onValidate?: (id: string) => void
  onCancel?: (id: string) => void
  onFeedback?: (id: string) => void
}

export function ValidationCard({
  id,
  title,
  description,
  source,
  process,
  agent_id,
  user_id,
  created_at,
  onValidate,
  onCancel,
  onFeedback,
}: ValidationCardProps) {
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

  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg">{title}</CardTitle>
            <CardDescription className="mt-1">{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">{source}</Badge>
          <Badge variant="secondary">{process}</Badge>
          {agent_id && <Badge variant="default">{agent_id}</Badge>}
        </div>

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{user_id}</span>
          <span>{formatDate(created_at)}</span>
        </div>

        <div className="flex gap-2 pt-2">
          <Button
            onClick={() => onValidate?.(id)}
            className="flex-1"
            variant="default"
          >
            <Check className="size-4 mr-2" />
            Valider
          </Button>
          <Button
            onClick={() => onCancel?.(id)}
            className="flex-1"
            variant="destructive"
          >
            <X className="size-4 mr-2" />
            Annuler
          </Button>
          <Button
            onClick={() => onFeedback?.(id)}
            className="flex-1"
            variant="outline"
          >
            <MessageSquare className="size-4 mr-2" />
            Feedback
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
