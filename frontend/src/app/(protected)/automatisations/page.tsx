"use client"

import { useState, useMemo } from 'react'
import { Plus, Zap } from 'lucide-react'
import { EntityListPage } from '@/components/layouts/entity-list-page'
import { AutomationCard } from '@/components/automations/automation-card'
import { AutomationDetailSheet } from '@/components/automations/automation-detail-sheet'
import { FeedbackDialog } from '@/components/automations/feedback-dialog'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { CascadeConfirmDialog } from '@/components/ui/cascade-confirm-dialog'
import { AutomationsFilters, AutomationsFiltersState } from '@/components/automations/automations-filters'
import { useAutomations, useToggleAutomation, useDeleteAutomation } from '@/services/automations/automations.hooks'
import { useChatContext } from '@/contexts/chat-context'
import type { Automation } from '@/services/automations/automations.types'

export default function AutomatisationsPage() {
  // State
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<AutomationsFiltersState>({})
  const [selectedAutomationId, setSelectedAutomationId] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [feedbackDialogOpen, setFeedbackDialogOpen] = useState(false)
  const [automationToModify, setAutomationToModify] = useState<Automation | null>(null)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [automationToDelete, setAutomationToDelete] = useState<string | null>(null)
  const [cascadeDialogOpen, setCascadeDialogOpen] = useState(false)
  const [deleteImpact, setDeleteImpact] = useState<any>(null)

  // Queries
  const { data: automations = [], isLoading, error } = useAutomations()
  const toggleMutation = useToggleAutomation()
  const deleteAutomation = useDeleteAutomation()

  // Chat context pour le débogage et la modification
  const { createChatWithParams, agents } = useChatContext()

  // Filtrage et tri
  const filteredAndSortedAutomations = useMemo(() => {
    let result = [...automations]

    // Filtrer par recherche
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter((auto) =>
        auto.name.toLowerCase().includes(query) ||
        auto.description?.toLowerCase().includes(query)
      )
    }

    // Filtrer par trigger type
    if (filters.triggerType) {
      result = result.filter((auto) =>
        auto.triggers?.some((t) => t.trigger_type === filters.triggerType && t.enabled)
      )
    }

    // Filtrer par date range
    if (filters.dateRange) {
      const now = new Date()
      const getDateThreshold = () => {
        switch (filters.dateRange) {
          case 'today':
            const today = new Date(now)
            today.setHours(0, 0, 0, 0)
            return today
          case 'week':
            const weekAgo = new Date(now)
            weekAgo.setDate(weekAgo.getDate() - 7)
            return weekAgo
          case 'month':
            const monthAgo = new Date(now)
            monthAgo.setMonth(monthAgo.getMonth() - 1)
            return monthAgo
          case 'year':
            const yearAgo = new Date(now)
            yearAgo.setFullYear(yearAgo.getFullYear() - 1)
            return yearAgo
          default:
            return null
        }
      }

      const threshold = getDateThreshold()
      if (threshold) {
        result = result.filter((auto) => new Date(auto.created_at) >= threshold)
      }
    }

    // Trier
    const sortBy = filters.sortBy || 'created-desc'
    result.sort((a, b) => {
      switch (sortBy) {
        case 'name-asc':
          return a.name.localeCompare(b.name)
        case 'name-desc':
          return b.name.localeCompare(a.name)
        case 'created-asc':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        case 'created-desc':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'success-rate-desc':
          return (b.stats?.success_rate || 0) - (a.stats?.success_rate || 0)
        case 'success-rate-asc':
          return (a.stats?.success_rate || 0) - (b.stats?.success_rate || 0)
        default:
          return 0
      }
    })

    return result
  }, [automations, searchQuery, filters])

  // Handlers
  const handleToggle = (id: string, enabled: boolean) => {
    toggleMutation.mutate({ id, enabled })
  }

  const handleCardClick = (id: string) => {
    setSelectedAutomationId(id)
    setSheetOpen(true)
  }

  const handleSheetClose = (open: boolean) => {
    setSheetOpen(open)
    if (!open) {
      setTimeout(() => setSelectedAutomationId(null), 300)
    }
  }

  const handleDebugAutomation = async (automation: Automation) => {
    const debugAgent = agents.find(a => a.is_system) || agents[0]
    if (!debugAgent) {
      console.error('No agent available for debugging')
      return
    }

    let debugPrompt = `# Débogage d'automatisation\n\n`
    debugPrompt += `**Automatisation :** ${automation.name}\n`
    debugPrompt += `**Description :** ${automation.description || 'Aucune description'}\n\n`

    if (automation.last_execution) {
      const lastExec = automation.last_execution
      debugPrompt += `## Dernière exécution\n`
      debugPrompt += `- **Statut :** ${lastExec.status}\n`
      debugPrompt += `- **Démarrage :** ${new Date(lastExec.started_at).toLocaleString('fr-FR')}\n`

      if (lastExec.status === 'failed') {
        debugPrompt += `- **Erreur détectée**\n\n`
      }
      debugPrompt += `\n`
    }

    if (automation.health_issues && automation.health_issues.length > 0) {
      debugPrompt += `## Problèmes détectés\n`
      automation.health_issues.forEach((issue, idx) => {
        debugPrompt += `${idx + 1}. ${issue}\n`
      })
      debugPrompt += `\n`
    }

    if (automation.stats) {
      debugPrompt += `## Statistiques\n`
      debugPrompt += `- **Exécutions totales :** ${automation.stats.total_executions}\n`
      debugPrompt += `- **Succès :** ${automation.stats.success_count}\n`
      debugPrompt += `- **Échecs :** ${automation.stats.failed_count}\n`
      debugPrompt += `- **Taux de réussite :** ${automation.stats.success_rate.toFixed(1)}%\n\n`
    }

    debugPrompt += `## Mission\n`
    debugPrompt += `J'ai besoin de ton aide pour analyser cette automatisation qui rencontre des problèmes. `
    debugPrompt += `Voici ce que j'attends de toi :\n\n`
    debugPrompt += `1. **Identifier la cause racine** de l'erreur ou du problème\n`
    debugPrompt += `2. **Effectuer des tests ou vérifications** si nécessaire pour confirmer le diagnostic\n`
    debugPrompt += `3. **Me proposer une solution** claire et détaillée pour réparer l'automatisation\n`
    debugPrompt += `4. **Me demander toute information supplémentaire** si tu en as besoin (logs, configuration, contexte, etc.)\n\n`
    debugPrompt += `N'hésite pas à me demander d'effectuer des manipulations ou de te fournir plus d'informations pour t'aider dans ton analyse.`

    await createChatWithParams({
      agentId: debugAgent.id,
      prompt: debugPrompt,
    })
  }

  const handleCreateAutomation = () => {
    // Ouvrir la modale avec null pour indiquer une création
    setAutomationToModify(null)
    setFeedbackDialogOpen(true)
  }

  const handleModifyAutomation = (automation: Automation) => {
    setAutomationToModify(automation)
    setFeedbackDialogOpen(true)
  }

  const handleFeedbackSubmit = async (feedback: string) => {
    const agent = agents.find(a => a.is_system) || agents[0]
    if (!agent) {
      console.error('No agent available')
      return
    }

    let prompt = ''

    // Mode création (automationToModify === null)
    if (!automationToModify) {
      prompt = `# Création d'une nouvelle automatisation\n\n`
      prompt += `## Demande\n\n`
      prompt += `${feedback}\n\n`
      prompt += `## Mission\n`
      prompt += `J'aimerais créer une nouvelle automatisation pilotée par IA selon ma demande ci-dessus. `
      prompt += `Voici ce que j'attends de toi :\n\n`
      prompt += `1. **Me poser des questions** pour bien comprendre ce que je veux automatiser\n`
      prompt += `2. **Identifier le type de déclencheur** approprié (webhook, schedule, event, etc.)\n`
      prompt += `3. **Définir les actions** que l'automatisation doit effectuer\n`
      prompt += `4. **Proposer une configuration complète** avec tous les paramètres nécessaires\n`
      prompt += `5. **M'expliquer comment l'automatisation fonctionnera** une fois créée\n\n`
      prompt += `N'hésite pas à me guider étape par étape et à me poser toutes les questions nécessaires pour créer une automatisation qui correspond exactement à mes besoins.`
    }
    // Mode modification
    else {
      prompt = `# Modification d'automatisation\n\n`
      prompt += `**Automatisation :** ${automationToModify.name}\n`
      prompt += `**Description actuelle :** ${automationToModify.description || 'Aucune description'}\n\n`

      if (automationToModify.triggers && automationToModify.triggers.length > 0) {
        prompt += `## Configuration actuelle\n`
        prompt += `**Triggers :** ${automationToModify.triggers.filter(t => t.enabled).map(t => t.trigger_type).join(', ')}\n\n`
      }

      if (automationToModify.stats) {
        prompt += `**Statistiques :** ${automationToModify.stats.total_executions} exécutions, ${automationToModify.stats.success_rate.toFixed(1)}% de réussite\n\n`
      }

      prompt += `## Demande de modification\n\n`
      prompt += `${feedback}\n\n`

      prompt += `## Mission\n`
      prompt += `J'aimerais modifier cette automatisation selon ma demande ci-dessus. `
      prompt += `Voici ce que j'attends de toi :\n\n`
      prompt += `1. **Analyser la demande** et comprendre les modifications souhaitées\n`
      prompt += `2. **Identifier les impacts** des changements demandés\n`
      prompt += `3. **Proposer une solution détaillée** pour implémenter ces modifications\n`
      prompt += `4. **Me guider étape par étape** pour réaliser ces changements\n`
      prompt += `5. **Me demander des clarifications** si ma demande n'est pas claire ou nécessite plus d'informations\n\n`
      prompt += `N'hésite pas à me poser des questions pour mieux comprendre mes besoins.`
    }

    await createChatWithParams({
      agentId: agent.id,
      prompt: prompt,
    })

    setAutomationToModify(null)
  }

  const handleDelete = (automationId: string) => {
    setAutomationToDelete(automationId)
    setDeleteConfirmOpen(true)
  }

  const confirmDelete = async () => {
    if (!automationToDelete) return

    try {
      await deleteAutomation.mutateAsync(automationToDelete)
      setDeleteConfirmOpen(false)
      setAutomationToDelete(null)
    } catch (error: any) {
      if (error.response?.status === 409 && error.response?.data?.detail?.type === 'confirmation_required') {
        setDeleteConfirmOpen(false)
        setDeleteImpact(error.response.data.detail.impact)
        setCascadeDialogOpen(true)
      } else {
        throw error
      }
    }
  }

  const confirmCascadeDelete = async () => {
    if (!automationToDelete) return

    try {
      await deleteAutomation.mutateAsync({
        id: automationToDelete,
        headers: { 'X-Confirm-Deletion': 'true' }
      })

      setCascadeDialogOpen(false)
      setDeleteImpact(null)
      setAutomationToDelete(null)
    } catch (error) {
      console.error('Error force deleting automation:', error)
    }
  }

  return (
    <>
      <EntityListPage
        title="Automatisations"
        description="Gérez vos automatisations pilotées par IA"
        searchPlaceholder="Rechercher une automatisation..."
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        createButton={{
          label: "Créer une automatisation",
          icon: Plus,
          onClick: handleCreateAutomation,
        }}
        filters={
          <AutomationsFilters
            filters={filters}
            onFiltersChange={setFilters}
          />
        }
        items={filteredAndSortedAutomations}
        isLoading={isLoading}
        error={error || null}
        renderItem={(automation) => (
          <AutomationCard
            automation={automation}
            onToggle={handleToggle}
            onClick={handleCardClick}
            onDebug={handleDebugAutomation}
            onModify={handleModifyAutomation}
            onDelete={() => handleDelete(automation.id)}
          />
        )}
        getItemKey={(automation) => automation.id}
        emptyState={{
          icon: Zap,
          title: "Aucune automatisation",
          description: "Les automatisations créées par l'IA apparaîtront ici"
        }}
        searchEmptyState={{
          icon: Zap,
          title: "Aucune automatisation trouvée",
          description: "Essayez de modifier vos filtres ou votre recherche"
        }}
        gridCols="md:grid-cols-2 lg:grid-cols-3"
      />

      {/* Dialogs */}
      <AutomationDetailSheet
        automationId={selectedAutomationId}
        open={sheetOpen}
        onOpenChange={handleSheetClose}
      />

      <FeedbackDialog
        open={feedbackDialogOpen}
        onOpenChange={setFeedbackDialogOpen}
        automation={automationToModify}
        onSubmit={handleFeedbackSubmit}
      />

      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title="Supprimer l'automatisation"
        description="Êtes-vous sûr de vouloir supprimer cette automatisation ? Cette action est irréversible."
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        onConfirm={confirmDelete}
        variant="destructive"
      />

      <CascadeConfirmDialog
        open={cascadeDialogOpen}
        onOpenChange={setCascadeDialogOpen}
        entityType="automatisation"
        entityName={deleteImpact?.automation_name || ""}
        impact={deleteImpact}
        onConfirm={confirmCascadeDelete}
        loading={deleteAutomation.isPending}
      />
    </>
  )
}
