"use client"

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { Automation } from '@/services/automations/automations.types'

interface FeedbackDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  automation: Automation | null
  onSubmit: (feedback: string) => void
}

export function FeedbackDialog({
  open,
  onOpenChange,
  automation,
  onSubmit,
}: FeedbackDialogProps) {
  const [feedback, setFeedback] = useState('')

  const handleSubmit = () => {
    if (feedback.trim()) {
      onSubmit(feedback)
      setFeedback('')
      onOpenChange(false)
    }
  }

  const handleCancel = () => {
    setFeedback('')
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Modifier l'automatisation</DialogTitle>
          <DialogDescription>
            {automation ? (
              <>
                Décrivez les modifications que vous souhaitez apporter à{' '}
                <span className="font-medium text-foreground">{automation.name}</span>
              </>
            ) : (
              "Décrivez les modifications que vous souhaitez apporter"
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <Textarea
            placeholder="Ex: J'aimerais que l'automatisation s'exécute toutes les heures au lieu de tous les jours, et qu'elle envoie une notification par email en cas d'échec..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            className="min-h-[120px] resize-none"
            autoFocus
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            Annuler
          </Button>
          <Button onClick={handleSubmit} disabled={!feedback.trim()}>
            Continuer avec l'IA
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
