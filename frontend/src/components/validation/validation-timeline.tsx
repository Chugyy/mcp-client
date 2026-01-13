"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { CheckCircle2, XCircle, MessageSquare, Clock, User, Wrench } from "lucide-react"
import type { Validation, ValidationLog } from "@/services/validations/validations.types"
import { format } from "date-fns"
import { fr } from "date-fns/locale"

interface ValidationTimelineProps {
  validation?: Validation
  logs: ValidationLog[]
}

export function ValidationTimeline({ validation, logs }: ValidationTimelineProps) {
  const getActionConfig = (action: string) => {
    switch (action) {
      case 'approved':
        return {
          label: 'Approuvé',
          icon: <CheckCircle2 className="size-3" />,
          className: 'bg-green-100 text-green-800 border-green-300 dark:bg-green-950 dark:text-green-300 dark:border-green-800'
        }
      case 'rejected':
        return {
          label: 'Rejeté',
          icon: <XCircle className="size-3" />,
          className: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300 dark:border-red-800'
        }
      case 'feedback':
        return {
          label: 'Feedback',
          icon: <MessageSquare className="size-3" />,
          className: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800'
        }
      default:
        return {
          label: action,
          icon: <Clock className="size-3" />,
          className: 'bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-950 dark:text-gray-300 dark:border-gray-800'
        }
    }
  }

  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Clock className="size-12 mb-4 opacity-50" />
        <p className="text-sm">Aucune action enregistrée</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Card de création (validation initiale) */}
      {validation && (
        <Card className="border !py-2 bg-muted/10">
          <CardContent className="px-3 space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <h4 className="font-medium text-sm">Validation créée</h4>
              <Badge variant="outline" className="gap-1 bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-900 dark:text-slate-300 dark:border-slate-700">
                <Clock className="size-3" />
                Créée
              </Badge>
            </div>

            <div className="text-xs text-muted-foreground">
              {format(new Date(validation.created_at), 'dd MMM yyyy à HH:mm', { locale: fr })}
            </div>

            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="details" className="border-0">
                <AccordionTrigger className="text-xs py-1.5 hover:no-underline">
                  Voir détails
                </AccordionTrigger>
                <AccordionContent className="space-y-3 pt-2">
                  <div className="space-y-2 text-xs">
                    <div className="flex items-start gap-2">
                      <User className="size-3 mt-0.5 text-muted-foreground" />
                      <div className="flex-1">
                        <div className="text-muted-foreground">Utilisateur</div>
                        <code className="text-xs">{validation.user_id}</code>
                      </div>
                    </div>
                    {validation.agent_id && (
                      <div className="flex items-start gap-2">
                        <User className="size-3 mt-0.5 text-muted-foreground" />
                        <div className="flex-1">
                          <div className="text-muted-foreground">Agent</div>
                          <code className="text-xs">{validation.agent_id}</code>
                        </div>
                      </div>
                    )}
                    {validation.tool_name && (
                      <div className="flex items-start gap-2">
                        <Wrench className="size-3 mt-0.5 text-muted-foreground" />
                        <div className="flex-1">
                          <div className="text-muted-foreground">Outil</div>
                          <code className="text-xs">{validation.tool_name}</code>
                        </div>
                      </div>
                    )}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </Card>
      )}

      {/* Cards des actions (logs) */}
      {logs.map((log) => {
        const actionConfig = getActionConfig(log.data.action)
        const formattedDate = format(new Date(log.created_at), 'dd MMM yyyy à HH:mm', { locale: fr })

        return (
          <Card key={log.id} className="border !py-2">
            <CardContent className="px-3 space-y-1.5">
              {/* Titre et Badge */}
              <div className="flex items-center justify-between gap-2">
                <h4 className="font-medium text-sm">
                  Action : {actionConfig.label}
                </h4>
                <Badge variant="outline" className={`gap-1 ${actionConfig.className}`}>
                  {actionConfig.icon}
                  {actionConfig.label}
                </Badge>
              </div>

              {/* Date */}
              <div className="text-xs text-muted-foreground">
                {formattedDate}
              </div>

              {/* Aperçu rapide selon l'action */}
              {log.data.action === 'rejected' && log.data.reason && (
                <div className="text-xs text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-950/20 p-2 rounded border border-red-200 dark:border-red-900">
                  <strong>Raison :</strong> {log.data.reason}
                </div>
              )}

              {log.data.action === 'feedback' && log.data.feedback && (
                <div className="text-xs text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/20 p-2 rounded border border-blue-200 dark:border-blue-900">
                  <strong>Feedback :</strong> {log.data.feedback}
                </div>
              )}

              {log.data.action === 'approved' && log.data.always_allow && (
                <div className="text-xs text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-950/20 p-2 rounded border border-green-200 dark:border-green-900">
                  ✓ Autorisation permanente activée
                </div>
              )}

              {/* Accordion pour plus de détails */}
              <Accordion type="single" collapsible className="w-full">
                <AccordionItem value="details" className="border-0">
                  <AccordionTrigger className="text-xs py-1.5 hover:no-underline">
                    Voir détails
                  </AccordionTrigger>
                  <AccordionContent className="space-y-3 pt-2">
                    {/* Action */}
                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-muted-foreground">
                        Action
                      </div>
                      <div className="text-xs bg-muted/50 p-2 rounded border">
                        {actionConfig.label}
                      </div>
                    </div>

                    {/* Tool Name */}
                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-muted-foreground">
                        Outil concerné
                      </div>
                      <div className="text-xs bg-muted/50 p-2 rounded border font-mono">
                        {log.data.tool_name}
                      </div>
                    </div>

                    {/* Reason (pour rejected) */}
                    {log.data.action === 'rejected' && log.data.reason && (
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-muted-foreground">
                          Raison du rejet
                        </div>
                        <div className="text-xs bg-red-50 dark:bg-red-950/20 p-2 rounded border border-red-200 dark:border-red-900">
                          {log.data.reason}
                        </div>
                      </div>
                    )}

                    {/* Feedback (pour feedback) */}
                    {log.data.action === 'feedback' && log.data.feedback && (
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-muted-foreground">
                          Feedback utilisateur
                        </div>
                        <div className="text-xs bg-blue-50 dark:bg-blue-950/20 p-2 rounded border border-blue-200 dark:border-blue-900">
                          {log.data.feedback}
                        </div>
                      </div>
                    )}

                    {/* Always Allow (pour approved) */}
                    {log.data.action === 'approved' && (
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-muted-foreground">
                          Autorisation permanente
                        </div>
                        <div className="text-xs bg-muted/50 p-2 rounded border">
                          {log.data.always_allow ? 'Oui - cet outil sera auto-approuvé à l\'avenir' : 'Non - validation requise pour les prochaines fois'}
                        </div>
                      </div>
                    )}

                    {/* User & Agent IDs */}
                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-muted-foreground">
                        Utilisateur
                      </div>
                      <div className="text-xs bg-muted/50 p-2 rounded border font-mono">
                        {log.user_id}
                      </div>
                    </div>

                    {log.agent_id && (
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-muted-foreground">
                          Agent
                        </div>
                        <div className="text-xs bg-muted/50 p-2 rounded border font-mono">
                          {log.agent_id}
                        </div>
                      </div>
                    )}

                    {/* Log ID */}
                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-muted-foreground">
                        Log ID
                      </div>
                      <div className="text-xs bg-muted/50 p-2 rounded border font-mono truncate">
                        {log.id}
                      </div>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
