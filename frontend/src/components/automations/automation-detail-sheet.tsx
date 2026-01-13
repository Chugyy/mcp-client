"use client"

import { useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import { DateTimePicker } from '@/components/ui/date-time-picker'
import { ExecutionTimeline } from './execution-timeline'
import { ValidationList } from './validation-card'
import { WorkflowVisualization } from './workflow-visualization'
import { useAutomation, useAutomationExecutions, useWorkflowSteps } from '@/services/automations/automations.hooks'
import { getValidationsByAutomationId } from '@/lib/mock-data/automations-mock'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { Shield, Copy, Check, Calendar as CalendarIcon, Zap } from 'lucide-react'
import { toast } from 'sonner'
import { DateRange } from 'react-day-picker'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

interface AutomationDetailSheetProps {
  automationId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AutomationDetailSheet({
  automationId,
  open,
  onOpenChange,
}: AutomationDetailSheetProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState<DateRange | undefined>()
  const [popoverOpen, setPopoverOpen] = useState(false)

  const copyToClipboard = async (text: string, label: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(label)
    toast.success(`${label} copié`)
    setTimeout(() => setCopiedId(null), 2000)
  }

  // Queries
  const { data: automation, isLoading: isLoadingAutomation } = useAutomation(automationId || '')
  const { data: executions, isLoading: isLoadingExecutions } = useAutomationExecutions(automationId || '')
  const { data: workflowSteps, isLoading: isLoadingSteps } = useWorkflowSteps(automationId || '')

  // Validations mockées
  const validations = automationId ? getValidationsByAutomationId(automationId) : []

  if (!automationId) return null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-md w-full overflow-y-auto p-0">
        <SheetTitle className="sr-only">Détails de l'automation</SheetTitle>
        <div className="px-4 pt-16 pb-4">
          <Tabs defaultValue="info" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="info">Infos</TabsTrigger>
              <TabsTrigger value="workflow">Workflow</TabsTrigger>
              <TabsTrigger value="history">Historique</TabsTrigger>
            </TabsList>

          {/* ONGLET 1 : INFORMATIONS */}
          <TabsContent value="info" className="space-y-4 mt-6">
            {isLoadingAutomation ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : automation ? (
              <>
                {/* Nom */}
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-lg">{automation.name}</h3>
                  {automation.is_system && (
                    <Shield className="size-4 text-blue-600 dark:text-blue-400" />
                  )}
                </div>

                {/* Description avec scroll (sans border/background) */}
                {automation.description && (
                  <p className="max-h-24 overflow-y-auto text-sm text-muted-foreground">
                    {automation.description}
                  </p>
                )}

                {/* Dates */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Créée le</span>
                    <span>{format(new Date(automation.created_at), 'dd MMM yyyy, HH:mm', { locale: fr })}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Mise à jour</span>
                    <span>{format(new Date(automation.updated_at), 'dd MMM yyyy, HH:mm', { locale: fr })}</span>
                  </div>
                </div>

                {/* Collapsible pour les IDs */}
                <Accordion type="single" collapsible className="w-full">
                  <AccordionItem value="ids" className="border-0">
                    <AccordionTrigger className="text-xs py-1.5 hover:no-underline">
                      Voir détails
                    </AccordionTrigger>
                    <AccordionContent className="space-y-3 pt-2">
                      {/* ID Automation */}
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-muted-foreground">
                          ID Automation
                        </div>
                        <div className="flex items-center gap-2 p-2 rounded bg-muted/50 font-mono text-xs border">
                          <code className="flex-1 truncate">{automation.id}</code>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0"
                            onClick={() => copyToClipboard(automation.id, 'ID Automation')}
                          >
                            {copiedId === 'ID Automation' ? (
                              <Check className="size-3 text-green-600" />
                            ) : (
                              <Copy className="size-3" />
                            )}
                          </Button>
                        </div>
                      </div>

                      {/* User ID */}
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-muted-foreground">
                          User ID
                        </div>
                        <div className="flex items-center gap-2 p-2 rounded bg-muted/50 font-mono text-xs border">
                          <code className="flex-1 truncate">{automation.user_id}</code>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0"
                            onClick={() => copyToClipboard(automation.user_id, 'User ID')}
                          >
                            {copiedId === 'User ID' ? (
                              <Check className="size-3 text-green-600" />
                            ) : (
                              <Copy className="size-3" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Automation introuvable
              </div>
            )}
          </TabsContent>

          {/* ONGLET 2 : WORKFLOW */}
          <TabsContent value="workflow" className="mt-6">
            {isLoadingSteps ? (
              <Skeleton className="h-[600px] w-full" />
            ) : workflowSteps && workflowSteps.length > 0 ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">Visualisation du workflow</h3>
                  <Badge variant="secondary" className="text-xs">
                    {workflowSteps.length} étape{workflowSteps.length > 1 ? 's' : ''}
                  </Badge>
                </div>
                <WorkflowVisualization steps={workflowSteps} />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <Zap className="size-16 opacity-50" />
                <div className="text-center">
                  <h3 className="text-lg font-semibold">Aucune étape configurée</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Ce workflow ne contient pas encore d'étapes
                  </p>
                </div>
              </div>
            )}
          </TabsContent>

          {/* ONGLET 3 : HISTORIQUE (EXECUTIONS + VALIDATIONS) */}
          <TabsContent value="history" className="space-y-4 mt-6">
            {/* Filtres */}
            <div className="flex flex-col gap-3">
              <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-left font-normal"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {dateRange?.from ? (
                      dateRange.to ? (
                        <>
                          {format(dateRange.from, "dd MMM yyyy", { locale: fr })} -{" "}
                          {format(dateRange.to, "dd MMM yyyy", { locale: fr })}
                        </>
                      ) : (
                        format(dateRange.from, "dd MMM yyyy", { locale: fr })
                      )
                    ) : (
                      <span>Sélectionner une période</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <DateTimePicker
                    mode="range"
                    selected={dateRange}
                    onSelect={setDateRange}
                    showTime={false}
                  />
                  <div className="border-t p-3 flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1"
                      onClick={() => {
                        setDateRange(undefined)
                        setPopoverOpen(false)
                      }}
                    >
                      Réinitialiser
                    </Button>
                    <Button
                      size="sm"
                      className="flex-1"
                      onClick={() => setPopoverOpen(false)}
                    >
                      Valider
                    </Button>
                  </div>
                </PopoverContent>
              </Popover>
            </div>

            {/* Timeline fusionnée */}
            {isLoadingExecutions ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : (
              <ExecutionTimeline
                executions={executions || []}
                validations={validations}
                dateRange={dateRange}
              />
            )}
          </TabsContent>
        </Tabs>
        </div>
      </SheetContent>
    </Sheet>
  )
}
