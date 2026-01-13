"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Clock, Loader2, CheckCircle2, XCircle, ShieldCheck, ShieldX, ShieldAlert } from "lucide-react"
import type { Execution, AutomationValidation } from "@/services/automations/automations.types"
import { format } from "date-fns"
import { fr } from "date-fns/locale"
import { DateRange } from "react-day-picker"

interface ExecutionTimelineProps {
  executions: Execution[]
  validations?: AutomationValidation[]
  filterType?: 'all' | 'executions' | 'validations'
  dateRange?: DateRange
}

type TimelineItem = {
  type: 'execution' | 'validation'
  date: Date
  data: Execution | AutomationValidation
}

export function ExecutionTimeline({ executions, validations = [], filterType = 'all', dateRange }: ExecutionTimelineProps) {
  // Formater la durée
  const formatDuration = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds}s`
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60)
      const remainingSeconds = seconds % 60
      return `${minutes}m ${remainingSeconds}s`
    } else {
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      const remainingSeconds = seconds % 60
      return `${hours}h ${minutes}m ${remainingSeconds}s`
    }
  }

  // Fusionner et trier les items par date
  const timelineItems: TimelineItem[] = [
    ...executions.map(exec => ({
      type: 'execution' as const,
      date: new Date(exec.started_at),
      data: exec
    })),
    ...validations.map(val => ({
      type: 'validation' as const,
      date: new Date(val.created_at),
      data: val
    }))
  ].sort((a, b) => b.date.getTime() - a.date.getTime())

  // Filtrer selon le type et la date
  const filteredItems = timelineItems.filter(item => {
    // Filtre de type
    if (filterType === 'executions' && item.type !== 'execution') return false
    if (filterType === 'validations' && item.type !== 'validation') return false

    // Filtre de plage de dates
    if (dateRange?.from) {
      const itemDate = item.date
      const fromDate = new Date(dateRange.from)
      fromDate.setHours(0, 0, 0, 0)

      if (itemDate < fromDate) return false

      if (dateRange.to) {
        const toDate = new Date(dateRange.to)
        toDate.setHours(23, 59, 59, 999)
        if (itemDate > toDate) return false
      }
    }

    return true
  })

  if (filteredItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Clock className="size-12 mb-4 opacity-50" />
        <p className="text-sm">Aucun élément pour le moment</p>
      </div>
    )
  }

  const getExecutionStatusConfig = (status: Execution['status']) => {
    switch (status) {
      case 'pending':
        return {
          label: 'En attente',
          icon: <Clock className="size-3" />,
          variant: 'secondary' as const,
          className: 'bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-900 dark:text-slate-300 dark:border-slate-700'
        }
      case 'running':
        return {
          label: 'En cours',
          icon: <Loader2 className="size-3 animate-spin" />,
          variant: 'default' as const,
          className: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800'
        }
      case 'success':
        return {
          label: 'Terminé',
          icon: <CheckCircle2 className="size-3" />,
          variant: 'outline' as const,
          className: 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800'
        }
      case 'failed':
        return {
          label: 'Échec',
          icon: <XCircle className="size-3" />,
          variant: 'destructive' as const,
          className: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800'
        }
    }
  }

  const getValidationStatusConfig = (status: AutomationValidation['status']) => {
    switch (status) {
      case 'pending':
        return {
          label: 'En attente',
          icon: <ShieldAlert className="size-3" />,
          variant: 'secondary' as const,
          className: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800'
        }
      case 'approved':
        return {
          label: 'Approuvée',
          icon: <ShieldCheck className="size-3" />,
          variant: 'outline' as const,
          className: 'bg-green-100 text-green-800 border-green-300 dark:bg-green-950 dark:text-green-300 dark:border-green-800'
        }
      case 'rejected':
        return {
          label: 'Rejetée',
          icon: <ShieldX className="size-3" />,
          variant: 'destructive' as const,
          className: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800'
        }
    }
  }

  // Fonction pour trouver la validation d'une execution
  const getValidationForExecution = (executionId: string) => {
    return validations.find(val => val.execution_id === executionId)
  }

  return (
    <div className="space-y-3">
      {filteredItems.map((item) => {
        if (item.type === 'execution') {
          const execution = item.data as Execution
          const statusConfig = getExecutionStatusConfig(execution.status)
          const validation = getValidationForExecution(execution.id)
          const formattedDate = format(item.date, 'dd MMM yyyy à HH:mm', { locale: fr })

        return (
          <Card key={execution.id} className="border !py-2">
            <CardContent className="px-3 space-y-1.5">
              {/* Titre et Badge */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium text-sm">
                    Execution #{execution.id.slice(-8)}
                  </h4>
                  {validation && (
                    <Badge
                      variant={getValidationStatusConfig(validation.status).variant}
                      className={`gap-1 text-xs ${getValidationStatusConfig(validation.status).className}`}
                    >
                      {getValidationStatusConfig(validation.status).icon}
                    </Badge>
                  )}
                </div>
                <Badge variant={statusConfig.variant} className={`gap-1 ${statusConfig.className}`}>
                  {statusConfig.icon}
                  {statusConfig.label}
                </Badge>
              </div>

              {/* Date avec durée */}
              <div className="text-xs text-muted-foreground">
                {formattedDate}
                {execution.completed_at && (
                  <span>
                    {' '}({formatDuration(Math.round(
                      (new Date(execution.completed_at).getTime() -
                        new Date(execution.started_at).getTime()) /
                        1000
                    ))})
                  </span>
                )}
              </div>

              {/* Accordion pour Input/Output */}
              <Accordion type="single" collapsible className="w-full">
                <AccordionItem value="details" className="border-0">
                  <AccordionTrigger className="text-xs py-1.5 hover:no-underline">
                    Voir détails
                  </AccordionTrigger>
                  <AccordionContent className="space-y-3 pt-2">
                    {/* Input (Params) */}
                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-muted-foreground">
                        Input
                      </div>
                      <pre className="text-xs bg-muted/50 p-3 rounded-md overflow-x-auto max-h-[200px] border">
                        <code>{JSON.stringify(execution.params, null, 2)}</code>
                      </pre>
                    </div>

                    {/* Output (Result ou Error) */}
                    {(execution.status === 'success' || execution.status === 'failed') && (
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-muted-foreground">
                          Output
                        </div>
                        <pre
                          className={`text-xs p-3 rounded-md overflow-x-auto max-h-[200px] border ${
                            execution.status === 'failed'
                              ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900'
                              : 'bg-muted/50'
                          }`}
                        >
                          <code>
                            {execution.status === 'success'
                              ? JSON.stringify(execution.result, null, 2)
                              : execution.error_message}
                          </code>
                        </pre>
                      </div>
                    )}
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </CardContent>
          </Card>
        )
        } else {
          // Card de validation standalone
          const validation = item.data as AutomationValidation
          const statusConfig = getValidationStatusConfig(validation.status)
          const formattedDate = format(item.date, 'dd MMM yyyy à HH:mm', { locale: fr })

          // Trouver l'execution liée pour afficher ses détails
          const linkedExecution = executions.find(exec => exec.id === validation.execution_id)

          return (
            <Card key={validation.id} className="border !py-2 bg-muted/20">
              <CardContent className="px-3 space-y-1.5">
                {/* Titre et Badge */}
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-medium text-sm">
                    Validation #{validation.id.slice(-8)}
                  </h4>
                  <Badge variant={statusConfig.variant} className={`gap-1 ${statusConfig.className}`}>
                    {statusConfig.icon}
                    {statusConfig.label}
                  </Badge>
                </div>

                {/* Date */}
                <div className="text-xs text-muted-foreground">
                  {formattedDate}
                </div>

                {/* Accordion pour les détails */}
                <Accordion type="single" collapsible className="w-full">
                  <AccordionItem value="details" className="border-0">
                    <AccordionTrigger className="text-xs py-1.5 hover:no-underline">
                      Voir détails
                    </AccordionTrigger>
                    <AccordionContent className="space-y-3 pt-2">
                      {/* Execution liée */}
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-muted-foreground">
                          Execution
                        </div>
                        <div className="text-xs bg-muted/50 p-2 rounded border">
                          #{validation.execution_id.slice(-8)}
                        </div>
                      </div>

                      {/* Date de validation */}
                      {validation.validated_at && (
                        <div className="space-y-1">
                          <div className="text-xs font-semibold text-muted-foreground">
                            Validée le
                          </div>
                          <div className="text-xs">
                            {format(new Date(validation.validated_at), 'dd MMMM yyyy à HH:mm', { locale: fr })}
                          </div>
                        </div>
                      )}

                      {/* Feedback */}
                      {validation.feedback && (
                        <div className="space-y-1">
                          <div className="text-xs font-semibold text-muted-foreground">
                            Feedback
                          </div>
                          <div className="text-xs bg-muted/50 p-2 rounded border">
                            {validation.feedback}
                          </div>
                        </div>
                      )}

                      {/* Input/Output de l'execution si disponible */}
                      {linkedExecution && (
                        <>
                          <div className="space-y-1">
                            <div className="text-xs font-semibold text-muted-foreground">
                              Input
                            </div>
                            <pre className="text-xs bg-muted/50 p-3 rounded-md overflow-x-auto max-h-[200px] border">
                              <code>{JSON.stringify(linkedExecution.params, null, 2)}</code>
                            </pre>
                          </div>

                          {(linkedExecution.status === 'success' || linkedExecution.status === 'failed') && (
                            <div className="space-y-1">
                              <div className="text-xs font-semibold text-muted-foreground">
                                Output
                              </div>
                              <pre
                                className={`text-xs p-3 rounded-md overflow-x-auto max-h-[200px] border ${
                                  linkedExecution.status === 'failed'
                                    ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900'
                                    : 'bg-muted/50'
                                }`}
                              >
                                <code>
                                  {linkedExecution.status === 'success'
                                    ? JSON.stringify(linkedExecution.result, null, 2)
                                    : linkedExecution.error_message}
                                </code>
                              </pre>
                            </div>
                          )}
                        </>
                      )}
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </CardContent>
            </Card>
          )
        }
      })}
    </div>
  )
}
