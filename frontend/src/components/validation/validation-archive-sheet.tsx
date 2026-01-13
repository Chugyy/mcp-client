"use client"

import { useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from '@/components/ui/sheet'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import { ValidationTimeline } from './validation-timeline'
import { useValidation, useValidationLogs } from '@/services/validations/validations.hooks'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { Shield, Copy, Check, MessageSquare } from 'lucide-react'
import { toast } from 'sonner'

interface ValidationArchiveSheetProps {
  validationId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ValidationArchiveSheet({
  validationId,
  open,
  onOpenChange,
}: ValidationArchiveSheetProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const copyToClipboard = async (text: string, label: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(label)
    toast.success(`${label} copié`)
    setTimeout(() => setCopiedId(null), 2000)
  }

  // Queries
  const { data: validation, isLoading: isLoadingValidation } = useValidation(validationId)
  const { data: logs, isLoading: isLoadingLogs } = useValidationLogs(validationId)

  if (!validationId) return null

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'pending':
        return {
          label: 'En attente',
          className: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800'
        }
      case 'approved':
        return {
          label: 'Approuvé',
          className: 'bg-green-100 text-green-800 border-green-300 dark:bg-green-950 dark:text-green-300 dark:border-green-800'
        }
      case 'rejected':
        return {
          label: 'Rejeté',
          className: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800'
        }
      case 'feedback':
        return {
          label: 'Feedback',
          className: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800'
        }
      default:
        return {
          label: status,
          className: 'bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-950 dark:text-gray-300 dark:border-gray-800'
        }
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-md w-full overflow-y-auto p-0">
        <SheetTitle className="sr-only">Détails de la validation</SheetTitle>
        <div className="px-4 pt-16 pb-4">
          <Tabs defaultValue="info" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="info">Infos</TabsTrigger>
              <TabsTrigger value="technical">Technique</TabsTrigger>
              <TabsTrigger value="history">Historique</TabsTrigger>
            </TabsList>

          {/* ONGLET 1 : INFORMATIONS */}
          <TabsContent value="info" className="space-y-4 mt-6">
            {isLoadingValidation ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : validation ? (
              <>
                {/* Titre et statut */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-lg">{validation.title}</h3>
                  </div>
                  <Badge variant="outline" className={getStatusConfig(validation.status).className}>
                    {getStatusConfig(validation.status).label}
                  </Badge>
                </div>

                {/* Description */}
                {validation.description && (
                  <p className="max-h-24 overflow-y-auto text-sm text-muted-foreground">
                    {validation.description}
                  </p>
                )}

                {/* Métadonnées principales */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Source</span>
                    <Badge variant="outline">{validation.source}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Process</span>
                    <Badge variant="secondary">{validation.process}</Badge>
                  </div>
                  {validation.tool_name && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Outil</span>
                      <span className="font-mono text-xs">{validation.tool_name}</span>
                    </div>
                  )}
                </div>

                {/* Dates */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Créée le</span>
                    <span>{format(new Date(validation.created_at), 'dd MMM yyyy, HH:mm', { locale: fr })}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Mise à jour</span>
                    <span>{format(new Date(validation.updated_at), 'dd MMM yyyy, HH:mm', { locale: fr })}</span>
                  </div>
                  {validation.expires_at && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Expire le</span>
                      <span>{format(new Date(validation.expires_at), 'dd MMM yyyy, HH:mm', { locale: fr })}</span>
                    </div>
                  )}
                </div>

                {/* Collapsible pour les IDs */}
                <Accordion type="single" collapsible className="w-full">
                  <AccordionItem value="ids" className="border-0">
                    <AccordionTrigger className="text-xs py-1.5 hover:no-underline">
                      Voir détails techniques
                    </AccordionTrigger>
                    <AccordionContent className="space-y-3 pt-2">
                      {/* ID Validation */}
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-muted-foreground">
                          ID Validation
                        </div>
                        <div className="flex items-center gap-2 p-2 rounded bg-muted/50 font-mono text-xs border">
                          <code className="flex-1 truncate">{validation.id}</code>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0"
                            onClick={() => copyToClipboard(validation.id, 'ID Validation')}
                          >
                            {copiedId === 'ID Validation' ? (
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
                          <code className="flex-1 truncate">{validation.user_id}</code>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0"
                            onClick={() => copyToClipboard(validation.user_id, 'User ID')}
                          >
                            {copiedId === 'User ID' ? (
                              <Check className="size-3 text-green-600" />
                            ) : (
                              <Copy className="size-3" />
                            )}
                          </Button>
                        </div>
                      </div>

                      {/* Agent ID */}
                      {validation.agent_id && (
                        <div className="space-y-1">
                          <div className="text-xs font-semibold text-muted-foreground">
                            Agent ID
                          </div>
                          <div className="flex items-center gap-2 p-2 rounded bg-muted/50 font-mono text-xs border">
                            <code className="flex-1 truncate">{validation.agent_id}</code>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 w-6 p-0"
                              onClick={() => copyToClipboard(validation.agent_id!, 'Agent ID')}
                            >
                              {copiedId === 'Agent ID' ? (
                                <Check className="size-3 text-green-600" />
                              ) : (
                                <Copy className="size-3" />
                              )}
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* Execution ID */}
                      {validation.execution_id && (
                        <div className="space-y-1">
                          <div className="text-xs font-semibold text-muted-foreground">
                            Execution ID
                          </div>
                          <div className="flex items-center gap-2 p-2 rounded bg-muted/50 font-mono text-xs border">
                            <code className="flex-1 truncate">{validation.execution_id}</code>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 w-6 p-0"
                              onClick={() => copyToClipboard(validation.execution_id!, 'Execution ID')}
                            >
                              {copiedId === 'Execution ID' ? (
                                <Check className="size-3 text-green-600" />
                              ) : (
                                <Copy className="size-3" />
                              )}
                            </Button>
                          </div>
                        </div>
                      )}
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Validation introuvable
              </div>
            )}
          </TabsContent>

          {/* ONGLET 2 : TECHNIQUE */}
          <TabsContent value="technical" className="space-y-4 mt-6">
            {isLoadingValidation ? (
              <Skeleton className="h-[400px] w-full" />
            ) : validation ? (
              <div className="space-y-4">
                {/* Tool Info */}
                {validation.tool_name && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold">Outil demandé</h4>
                    <div className="p-3 rounded-md bg-muted/50 border">
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Nom</span>
                          <code className="text-xs">{validation.tool_name}</code>
                        </div>
                        {validation.server_id && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Serveur</span>
                            <code className="text-xs">{validation.server_id}</code>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Input (Arguments) */}
                {validation.tool_args && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold">Arguments (Input)</h4>
                    <pre className="text-xs bg-muted/50 p-3 rounded-md overflow-x-auto max-h-[300px] border">
                      <code>{JSON.stringify(validation.tool_args, null, 2)}</code>
                    </pre>
                  </div>
                )}

                {/* Output (Result) */}
                {validation.tool_result && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold">Résultat (Output)</h4>
                    <pre className="text-xs bg-muted/50 p-3 rounded-md overflow-x-auto max-h-[300px] border">
                      <code>{JSON.stringify(validation.tool_result, null, 2)}</code>
                    </pre>
                  </div>
                )}

                {!validation.tool_name && !validation.tool_args && !validation.tool_result && (
                  <div className="text-center py-12 text-muted-foreground">
                    <MessageSquare className="size-12 mx-auto mb-4 opacity-50" />
                    <p className="text-sm">Aucune donnée technique disponible</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Validation introuvable
              </div>
            )}
          </TabsContent>

          {/* ONGLET 3 : HISTORIQUE */}
          <TabsContent value="history" className="space-y-4 mt-6">
            {isLoadingLogs ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : (
              <ValidationTimeline
                validation={validation || undefined}
                logs={logs || []}
              />
            )}
          </TabsContent>
        </Tabs>
        </div>
      </SheetContent>
    </Sheet>
  )
}
