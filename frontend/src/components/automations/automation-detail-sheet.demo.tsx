"use client"

/**
 * FICHIER DE DÉMONSTRATION TEMPORAIRE
 * Pour tester AutomationDetailSheet
 *
 * Usage:
 * import { AutomationDetailSheetDemo } from '@/components/automations/automation-detail-sheet.demo'
 */

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { AutomationDetailSheet } from './automation-detail-sheet'

export function AutomationDetailSheetDemo() {
  const [open, setOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const testAutomationIds = ['auto_001', 'auto_002', 'auto_003']

  return (
    <div className="space-y-4 p-4">
      <h2 className="text-lg font-semibold">AutomationDetailSheet - Démo</h2>
      <div className="flex gap-2">
        {testAutomationIds.map((id) => (
          <Button
            key={id}
            onClick={() => {
              setSelectedId(id)
              setOpen(true)
            }}
          >
            Ouvrir {id}
          </Button>
        ))}
      </div>

      <AutomationDetailSheet
        automationId={selectedId}
        open={open}
        onOpenChange={setOpen}
      />
    </div>
  )
}
