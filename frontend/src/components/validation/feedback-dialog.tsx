"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { MessageSquare } from "lucide-react"

interface FeedbackDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  itemTitle: string
  onSubmit: (feedback: string) => void
}

export function FeedbackDialog({
  open,
  onOpenChange,
  itemTitle,
  onSubmit,
}: FeedbackDialogProps) {
  const [feedback, setFeedback] = useState("")

  const handleSubmit = () => {
    if (feedback.trim()) {
      onSubmit(feedback)
      setFeedback("")
      onOpenChange(false)
    }
  }

  const handleCancel = () => {
    setFeedback("")
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="size-5" />
            Demander un feedback
          </DialogTitle>
          <DialogDescription>
            Vous allez demander un feedback pour : <strong>{itemTitle}</strong>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <label htmlFor="feedback" className="text-sm font-medium">
            Votre message (optionnel)
          </label>
          <Textarea
            id="feedback"
            placeholder="Ajoutez un commentaire ou une question..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={4}
            className="resize-none"
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            Annuler
          </Button>
          <Button onClick={handleSubmit}>
            Envoyer la demande
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
