/**
 * EXEMPLE D'INTÉGRATION COMPLÈTE
 *
 * Ce fichier montre comment intégrer AutomationDetailSheet
 * dans une page d'automations avec une liste.
 *
 * COPIEZ CE CODE DANS VOTRE PAGE D'AUTOMATIONS
 */

"use client"

import { useState } from 'react'
import { AutomationCard, AutomationDetailSheet } from '@/components/automations'
import { useAutomations } from '@/services/automations/automations.hooks'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Plus } from 'lucide-react'

export function AutomationsPageExample() {
  // État pour le sheet
  const [selectedAutomationId, setSelectedAutomationId] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  // Récupération des automations
  const { data: automations = [], isLoading, error } = useAutomations()

  // Handler pour ouvrir le sheet
  const handleOpenDetails = (automationId: string) => {
    setSelectedAutomationId(automationId)
    setSheetOpen(true)
  }

  // Handler pour fermer le sheet
  const handleCloseSheet = (open: boolean) => {
    setSheetOpen(open)
    if (!open) {
      // Optionnel : réinitialiser l'ID après la fermeture
      setTimeout(() => setSelectedAutomationId(null), 300)
    }
  }

  return (
    <div className="container mx-auto py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Automations</h1>
          <p className="text-muted-foreground">
            Gérez vos automations et consultez leur historique
          </p>
        </div>
        <Button>
          <Plus className="size-4 mr-2" />
          Nouvelle automation
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/20 p-4">
          <p className="text-sm text-red-800 dark:text-red-200">
            Erreur lors du chargement des automations
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && automations.length === 0 && (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <p className="text-muted-foreground mb-4">Aucune automation pour le moment</p>
          <Button>
            <Plus className="size-4 mr-2" />
            Créer votre première automation
          </Button>
        </div>
      )}

      {/* Liste des automations */}
      {!isLoading && !error && automations.length > 0 && (
        <div className="grid gap-4">
          {automations.map((automation) => (
            <AutomationCard
              key={automation.id}
              automation={automation}
              // Passez le handler pour ouvrir le sheet
              onViewDetails={() => handleOpenDetails(automation.id)}
            />
          ))}
        </div>
      )}

      {/* Sheet de détails */}
      <AutomationDetailSheet
        automationId={selectedAutomationId}
        open={sheetOpen}
        onOpenChange={handleCloseSheet}
      />
    </div>
  )
}

/**
 * ALTERNATIVE AVEC DONNÉES MOCKÉES (POUR LES TESTS)
 */
export function AutomationsPageExampleWithMockData() {
  const [selectedAutomationId, setSelectedAutomationId] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  // IDs mockés disponibles
  const mockAutomationIds = ['auto_001', 'auto_002', 'auto_003']

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight mb-2">Automations - Démo</h1>
        <p className="text-muted-foreground">Cliquez sur un bouton pour ouvrir le sheet</p>
      </div>

      <div className="flex gap-4">
        {mockAutomationIds.map((id) => (
          <Button
            key={id}
            onClick={() => {
              setSelectedAutomationId(id)
              setSheetOpen(true)
            }}
            variant="outline"
          >
            Automation {id.split('_')[1]}
          </Button>
        ))}
      </div>

      <AutomationDetailSheet
        automationId={selectedAutomationId}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
      />
    </div>
  )
}

/**
 * EXEMPLE AVEC TABLE (SI VOUS UTILISEZ UNE TABLE AU LIEU DE CARDS)
 */
export function AutomationsTableExample() {
  const [selectedAutomationId, setSelectedAutomationId] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const { data: automations = [] } = useAutomations()

  return (
    <div className="container mx-auto py-8 space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Automations</h1>

      {/* Table simple */}
      <div className="rounded-lg border">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-3 text-left text-sm font-medium">Nom</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {automations.map((automation) => (
              <tr key={automation.id} className="border-b last:border-0">
                <td className="px-4 py-3">{automation.name}</td>
                <td className="px-4 py-3">{automation.status}</td>
                <td className="px-4 py-3">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedAutomationId(automation.id)
                      setSheetOpen(true)
                    }}
                  >
                    Détails
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <AutomationDetailSheet
        automationId={selectedAutomationId}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
      />
    </div>
  )
}
