"use client"

import { Eye, Zap, Wrench, Clock, CalendarClock, CheckCircle2, XCircle, AlertCircle, Edit, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { EntityCard } from '@/components/ui/entity-card'
import type { Automation } from '@/services/automations/automations.types'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'

interface AutomationCardProps {
  automation: Automation
  onToggle: (id: string, enabled: boolean) => void
  onClick: (id: string) => void
  onDebug?: (automation: Automation) => void
  onModify?: (automation: Automation) => void
  onDelete?: (id: string) => void
}

function getTriggerLabel(trigger_type: string): string {
  const labels: Record<string, string> = {
    cron: 'CRON',
    webhook: 'Webhook',
    date: 'Date',
    event: 'Événement',
    manual: 'Manuel'
  }
  return labels[trigger_type] || trigger_type
}

export function AutomationCard({ automation, onToggle, onClick, onDebug, onModify, onDelete }: AutomationCardProps) {
  const lastExecution = automation.last_execution
  const triggers = automation.triggers || []
  const healthStatus = automation.health_status || 'healthy'
  const stats = automation.stats

  return (
    <EntityCard
      icon={Zap}
      title={automation.name}
      description={automation.description || "Aucune description"}
      descriptionLines={2}

      enableToggle
      toggleValue={automation.enabled}
      onToggle={(checked) => onToggle(automation.id, checked)}
      toggleDisabled={automation.is_system}

      actions={[
        {
          icon: Edit,
          onClick: () => onModify?.(automation),
          title: "Modifier avec IA",
          variant: 'ghost',
        },
        {
          icon: Wrench,
          onClick: () => onDebug?.(automation),
          title: "Déboguer avec IA",
          variant: 'ghost',
          disabled: healthStatus === 'healthy',
          className: cn(
            healthStatus === 'warning' && "text-orange-500",
            healthStatus === 'error' && "text-red-500 animate-pulse"
          )
        },
        {
          icon: Eye,
          onClick: () => onClick(automation.id),
          title: "Voir les détails"
        },
        {
          icon: Trash2,
          onClick: () => onDelete?.(automation.id),
          title: "Supprimer",
          variant: 'ghost',
          className: "text-destructive hover:text-destructive",
          disabled: automation.is_system
        }
      ]}

      afterDescription={
        <div className="space-y-2">
          {/* Dernière exécution - Toujours affichée */}
          <div className="flex items-center gap-2 text-xs">
            <Clock className="size-3 text-muted-foreground" />
            <span className="text-muted-foreground">Dernière exec:</span>
            {lastExecution ? (
              <div className="flex items-center gap-1">
                {lastExecution.status === 'success' && <CheckCircle2 className="size-3 text-green-600" />}
                {lastExecution.status === 'failed' && <XCircle className="size-3 text-red-600" />}
                {lastExecution.status === 'running' && <div className="size-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />}
                <span className="text-xs">
                  {formatDistanceToNow(new Date(lastExecution.started_at), { locale: fr, addSuffix: true })}
                </span>
              </div>
            ) : (
              <span className="text-xs text-muted-foreground/60">Jamais exécutée</span>
            )}
          </div>

          {/* Triggers - Toujours affichée */}
          <div className="flex items-center gap-2 text-xs">
            <CalendarClock className="size-3 text-muted-foreground" />
            <span className="text-muted-foreground">Triggers:</span>
            {triggers.length > 0 ? (
              <div className="flex gap-1">
                {triggers.filter(t => t.enabled).slice(0, 2).map((trigger, idx) => (
                  <Badge key={idx} variant="outline" className="text-xs">
                    {getTriggerLabel(trigger.trigger_type)}
                  </Badge>
                ))}
                {triggers.filter(t => t.enabled).length > 2 && (
                  <Badge variant="outline" className="text-xs">
                    +{triggers.filter(t => t.enabled).length - 2}
                  </Badge>
                )}
              </div>
            ) : (
              <span className="text-xs text-muted-foreground/60">Aucun</span>
            )}
          </div>

          {/* Health issues - Toujours affichée */}
          <div className="flex items-start gap-2 text-xs">
            <AlertCircle className={cn(
              "size-3 mt-0.5",
              healthStatus === 'healthy' && "text-muted-foreground/60",
              healthStatus === 'warning' && "text-orange-500",
              healthStatus === 'error' && "text-red-500"
            )} />
            {healthStatus !== 'healthy' && automation.health_issues && automation.health_issues.length > 0 ? (
              <span className={cn(
                "text-xs",
                healthStatus === 'warning' && "text-orange-600",
                healthStatus === 'error' && "text-red-600"
              )}>
                {automation.health_issues[0]}
              </span>
            ) : (
              <span className="text-xs text-muted-foreground/60">Aucun problème</span>
            )}
          </div>

          {/* Stats - Toujours affichée */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {stats && stats.total_executions > 0 ? (
              <>
                <span>{stats.total_executions} exec</span>
                <span>•</span>
                <span className="text-green-600">{stats.success_rate.toFixed(0)}% réussite</span>
              </>
            ) : (
              <span className="text-muted-foreground/60">Aucune statistique</span>
            )}
          </div>
        </div>
      }

      isSystem={automation.is_system}
    />
  )
}
