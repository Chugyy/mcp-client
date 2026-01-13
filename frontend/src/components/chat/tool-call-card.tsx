"use client"

import { useState } from "react"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Check, X, MessageSquare, CheckCheck, Loader2, CheckCircle2, XCircle, Clock, ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

interface ToolCallCardProps {
  toolName: string
  step: 'validation_requested' | 'executing' | 'completed' | 'failed' | 'rejected' | 'feedback_received' | 'cancelled'
  arguments: Record<string, any>
  result?: {
    success: boolean
    result?: any
    error?: string
  }
  validationId?: string
  status?: 'pending' | 'approved' | 'rejected' | 'cancelled'
  onApprove?: (validationId: string, alwaysAllow: boolean) => void
  onReject?: (validationId: string, reason?: string) => void
  onFeedback?: (validationId: string, feedback: string) => void
}

export function ToolCallCard({
  toolName,
  step,
  arguments: args,
  result,
  validationId,
  status,
  onApprove,
  onReject,
  onFeedback,
}: ToolCallCardProps) {
  const [feedbackText, setFeedbackText] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  // Badge et icône dynamique configuration
  const stateConfig = {
    validation_requested: {
      label: 'EN ATTENTE',
      variant: 'secondary' as const,
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      icon: Clock,
      iconClassName: 'text-yellow-600 dark:text-yellow-400',
      borderColor: 'border-l-yellow-500'
    },
    executing: {
      label: 'EN COURS',
      variant: 'default' as const,
      className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      icon: Loader2,
      iconClassName: 'text-blue-600 dark:text-blue-400 animate-spin',
      borderColor: 'border-l-blue-500'
    },
    completed: {
      label: 'TERMINÉ',
      variant: 'default' as const,
      className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      icon: CheckCircle2,
      iconClassName: 'text-green-600 dark:text-green-400',
      borderColor: 'border-l-green-500'
    },
    failed: {
      label: 'ÉCHEC',
      variant: 'destructive' as const,
      className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      icon: XCircle,
      iconClassName: 'text-red-600 dark:text-red-400',
      borderColor: 'border-l-red-500'
    },
    rejected: {
      label: 'REJETÉ',
      variant: 'outline' as const,
      className: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
      icon: X,
      iconClassName: 'text-gray-600 dark:text-gray-400',
      borderColor: 'border-l-gray-500'
    },
    feedback_received: {
      label: 'FEEDBACK',
      variant: 'secondary' as const,
      className: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
      icon: MessageSquare,
      iconClassName: 'text-orange-600 dark:text-orange-400',
      borderColor: 'border-l-orange-500'
    },
    cancelled: {
      label: 'ANNULÉ',
      variant: 'outline' as const,
      className: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
      icon: XCircle,
      iconClassName: 'text-gray-600 dark:text-gray-400',
      borderColor: 'border-l-gray-500'
    },
  }

  const state = stateConfig[step]
  const StateIcon = state.icon
  const showActions =
    step === 'validation_requested' &&
    status === 'pending'
  const hasOutput = result && (step === 'completed' || step === 'failed')

  const handleFeedbackSubmit = () => {
    if (feedbackText.trim() && validationId) {
      onFeedback?.(validationId, feedbackText)
      setFeedbackText('')
      setDialogOpen(false)
    }
  }

  const handleRejectSubmit = () => {
    if (validationId) {
      onReject?.(validationId, rejectReason.trim() || undefined)
      setRejectReason('')
      setRejectDialogOpen(false)
    }
  }

  return (
    <Collapsible defaultOpen={false} className="my-4 w-full max-w-full">
      <div className={cn(
        "border border-border rounded-lg overflow-hidden",
        "border-l-4",
        state.borderColor
      )}>
        <CollapsibleTrigger className="flex items-center justify-between w-full p-3 hover:bg-muted/20 transition-colors">
          <div className="flex items-center gap-3">
            {/* Icône d'état */}
            <StateIcon className={cn("size-4", state.iconClassName)} />

            {/* Nom de l'outil */}
            <span className="font-medium text-sm">{toolName}</span>

            {/* Badge état */}
            <Badge variant={state.variant} className={state.className}>
              {state.label}
            </Badge>
          </div>

          {/* Chevron toggle */}
          <ChevronDown className="size-4 text-muted-foreground transition-transform duration-200 data-[state=open]:rotate-180" />
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="border-t border-border p-3 space-y-3 max-w-full">
            {/* Arguments */}
            <div className="min-w-0">
              <div className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1">
                📝 Arguments
              </div>
              <pre className="text-xs bg-muted/20 p-3 rounded border border-border overflow-x-auto overflow-y-auto max-h-[300px] break-all whitespace-pre-wrap">
                <code className="break-all">{JSON.stringify(args, null, 2)}</code>
              </pre>
            </div>

            {/* Output (si disponible) */}
            {hasOutput && (
              <div className="min-w-0">
                <div className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1">
                  {step === 'completed' ? '✅ Output' : '❌ Erreur'}
                </div>
                <pre className={cn(
                  "text-xs p-3 rounded border overflow-x-auto overflow-y-auto max-h-[300px] break-all whitespace-pre-wrap",
                  step === 'failed'
                    ? 'bg-red-50/30 border-red-200 dark:bg-red-950/20 dark:border-red-900'
                    : 'bg-muted/20 border-border'
                )}>
                  <code className="break-all">{JSON.stringify(result, null, 2)}</code>
                </pre>
              </div>
            )}

            {/* Message d'état pour executing */}
            {step === 'executing' && (
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <div className="size-2 rounded-full bg-blue-500 animate-pulse" />
                Exécution en cours...
              </div>
            )}

            {step === 'rejected' && (
              <div className="text-sm text-muted-foreground">
                ❌ Outil rejeté par l'utilisateur
              </div>
            )}

            {step === 'feedback_received' && (
              <div className="text-sm text-muted-foreground">
                💬 Feedback envoyé au LLM
              </div>
            )}

            {step === 'cancelled' && (
              <div className="text-sm text-muted-foreground">
                ⛔ Annulé par l'utilisateur (stop pendant validation)
              </div>
            )}
          </div>
        </CollapsibleContent>

        {/* Actions de validation */}
        {showActions && validationId && (
          <div className="border-t border-border p-3">
            <div className="grid grid-cols-4 gap-2">
            {/* Bouton Refuser avec Dialog */}
            <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  size="sm"
                  variant="destructive"
                  className="flex items-center gap-1"
                >
                  <X className="size-3" />
                  Refuser
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Refuser l'outil</DialogTitle>
                  <DialogDescription>
                    Vous pouvez indiquer une raison pour le refus (optionnel).
                  </DialogDescription>
                </DialogHeader>
                <Textarea
                  placeholder="Ex: Cet outil ne devrait pas être utilisé dans ce contexte"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  rows={3}
                />
                <DialogFooter>
                  <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>
                    Annuler
                  </Button>
                  <Button variant="destructive" onClick={handleRejectSubmit}>
                    Confirmer le refus
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {/* Bouton Valider une fois */}
            <Button
              size="sm"
              variant="default"
              onClick={() => onApprove?.(validationId, false)}
              className="flex items-center gap-1"
            >
              <Check className="size-3" />
              Une fois
            </Button>

            {/* Bouton Valider toujours */}
            <Button
              size="sm"
              variant="default"
              onClick={() => onApprove?.(validationId, true)}
              className="flex items-center gap-1 bg-green-600 hover:bg-green-700"
            >
              <CheckCheck className="size-3" />
              Toujours
            </Button>

            {/* Bouton Feedback avec Dialog */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  size="sm"
                  variant="outline"
                  className="flex items-center gap-1"
                >
                  <MessageSquare className="size-3" />
                  Feedback
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Envoyer un feedback</DialogTitle>
                  <DialogDescription>
                    Le LLM recevra votre feedback et pourra ajuster son approche au lieu d'exécuter l'outil directement.
                  </DialogDescription>
                </DialogHeader>
                <Textarea
                  placeholder="Ex: Utilise plutôt Paris au lieu de Lyon pour cette recherche"
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  rows={4}
                />
                <DialogFooter>
                  <Button variant="outline" onClick={() => setDialogOpen(false)}>
                    Annuler
                  </Button>
                  <Button onClick={handleFeedbackSubmit} disabled={!feedbackText.trim()}>
                    Envoyer le feedback
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            </div>
          </div>
        )}
      </div>
    </Collapsible>
  )
}
