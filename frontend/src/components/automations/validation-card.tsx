"use client"

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Clock, CheckCircle2, XCircle } from 'lucide-react'
import type { AutomationValidation } from '@/services/automations/automations.types'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

interface ValidationCardProps {
  validation: AutomationValidation
}

export function ValidationCard({ validation }: ValidationCardProps) {
  // Configuration selon le status
  const getStatusConfig = (status: AutomationValidation['status']) => {
    switch (status) {
      case 'pending':
        return {
          label: 'EN ATTENTE',
          icon: <Clock className="size-4 text-yellow-600 dark:text-yellow-400" />,
          className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
        }
      case 'approved':
        return {
          label: 'APPROUVÉE',
          icon: <CheckCircle2 className="size-4 text-green-600 dark:text-green-400" />,
          className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        }
      case 'rejected':
        return {
          label: 'REJETÉE',
          icon: <XCircle className="size-4 text-red-600 dark:text-red-400" />,
          className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        }
    }
  }

  const statusConfig = getStatusConfig(validation.status)

  return (
    <Card className="border-l-4 border-l-primary/50">
      <CardContent className="px-4 py-3 space-y-2">
        {/* Header avec badge */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">
              Validation #{validation.id.slice(-3)}
            </span>
          </div>
          <Badge variant="outline" className={statusConfig.className}>
            {statusConfig.icon}
            <span className="ml-1">{statusConfig.label}</span>
          </Badge>
        </div>

        {/* Accordion pour les détails */}
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="details" className="border-b-0">
            <AccordionTrigger className="text-sm py-2 hover:no-underline">
              Détails
            </AccordionTrigger>
            <AccordionContent className="space-y-2">
              {/* Execution ID */}
              <div>
                <div className="text-xs font-semibold text-muted-foreground mb-1">
                  Execution
                </div>
                <code className="text-xs bg-muted/50 px-2 py-1 rounded">
                  {validation.execution_id}
                </code>
              </div>

              {/* Dates */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="text-xs font-semibold text-muted-foreground mb-1">
                    Créée le
                  </div>
                  <p className="text-xs">
                    {format(new Date(validation.created_at), 'dd MMM yyyy HH:mm', { locale: fr })}
                  </p>
                </div>
                {validation.validated_at && (
                  <div>
                    <div className="text-xs font-semibold text-muted-foreground mb-1">
                      Validée le
                    </div>
                    <p className="text-xs">
                      {format(new Date(validation.validated_at), 'dd MMM yyyy HH:mm', { locale: fr })}
                    </p>
                  </div>
                )}
              </div>

              {/* Feedback si présent */}
              {validation.feedback && (
                <div>
                  <div className="text-xs font-semibold text-muted-foreground mb-1">
                    Feedback
                  </div>
                  <p className="text-sm bg-muted/50 p-2 rounded border">
                    {validation.feedback}
                  </p>
                </div>
              )}

              {/* Note READ-ONLY */}
              <div className="text-xs text-muted-foreground italic pt-2 border-t">
                💡 Cette validation est en lecture seule
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </CardContent>
    </Card>
  )
}

// Composant de liste avec empty state
interface ValidationListProps {
  validations: AutomationValidation[]
}

export function ValidationList({ validations }: ValidationListProps) {
  if (validations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Clock className="size-12 mb-4 opacity-50" />
        <p className="text-sm">Aucune validation pour le moment</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Note sur les données mockées */}
      <div className="text-sm bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 rounded-lg p-3">
        🚧 <strong>Données mockées</strong> - Les validations affichées sont temporaires.
        Les endpoints backend sont en cours d&apos;implémentation.
      </div>

      {/* Liste des validations */}
      {validations.map((validation) => (
        <ValidationCard key={validation.id} validation={validation} />
      ))}
    </div>
  )
}
