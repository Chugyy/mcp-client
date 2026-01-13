"use client"

import { useState, useEffect } from "react"
import { Search, Plus, Users, Bot } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { AgentCard } from "@/components/agents/card"
import { AgentModal } from "@/components/agents/modal"
import { TeamCard } from "@/components/agents/team-card"
import { TeamModal } from "@/components/agents/team-modal"
import { ConfirmDialog } from "@/components/ui/confirm-dialog"
import { CascadeConfirmDialog } from "@/components/ui/cascade-confirm-dialog"
import { useChatContext } from "@/contexts/chat-context"
import { AppLayout } from "@/components/layouts/app-layout"
import type { Team, AgentCapability } from "@/lib/api"
import { extractErrorMessage } from "@/lib/error-handler"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  useAgents,
  useCreateAgent,
  useUpdateAgent,
  useDeleteAgent,
  useDuplicateAgent,
  useToggleAgent,
} from "@/services/agents/agents.hooks"
import type { Agent as AgentType } from "@/services/agents/agents.types"

interface AgentFormData {
  id?: string
  name: string
  description?: string
  avatar?: string | File
  tags?: string[]
  system_prompt: string
  documents?: File[]
  youtube_url?: string
  capabilities?: AgentCapability[]
  mcp_configs?: any[]
  resources?: any[]
}

export default function AgentsPage() {
  // TODO: userId devrait venir du contexte auth quand les teams seront réactivées
  const userId = "" // Temporaire - Teams désactivés

  // React Query hooks for agents
  const { data: agents = [], isLoading: isLoadingAgents } = useAgents()
  const createAgent = useCreateAgent()
  const updateAgent = useUpdateAgent()
  const deleteAgent = useDeleteAgent()
  const duplicateAgent = useDuplicateAgent()
  const toggleAgent = useToggleAgent()

  // UI state
  const [searchQuery, setSearchQuery] = useState("")
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState<AgentFormData | undefined>()
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [agentToDelete, setAgentToDelete] = useState<string | null>(null)
  const [cascadeDialogOpen, setCascadeDialogOpen] = useState(false)
  const [deleteImpact, setDeleteImpact] = useState<any>(null)

  // Teams state (unchanged)
  const [teams, setTeams] = useState<Team[]>([])
  const [isTeamModalOpen, setIsTeamModalOpen] = useState(false)
  const [selectedTeam, setSelectedTeam] = useState<Team | undefined>()
  const [deleteTeamConfirmOpen, setDeleteTeamConfirmOpen] = useState(false)
  const [teamToDelete, setTeamToDelete] = useState<string | null>(null)

  // Check if any mutation is pending
  const isMutating =
    createAgent.isPending ||
    updateAgent.isPending ||
    deleteAgent.isPending ||
    duplicateAgent.isPending ||
    toggleAgent.isPending

  // Teams sont temporairement désactivés, donc pas besoin de charger
  // useEffect(() => {
  //   const loadTeams = async () => {
  //     if (!userId) return
  //     try {
  //       const { getTeams } = await import("@/lib/api")
  //       const fetchedTeams = await getTeams(userId)
  //       setTeams(fetchedTeams)
  //     } catch (error) {
  //       console.error("Failed to load teams:", error)
  //     }
  //   }
  //   loadTeams()
  // }, [userId])

  // Agent handlers
  const handleEdit = (agentId: string) => {
    const agent = agents.find((a) => a.id === agentId)
    if (agent) {
      const agentData = {
        id: agent.id,
        name: agent.name,
        description: agent.description || "",
        avatar: (agent as any).avatar_url || "",
        tags: agent.tags || [],
        system_prompt: agent.system_prompt,
        documents: [],
        mcp_configs: (agent as any).mcp_configs || [],
        resources: (agent as any).resources || [],
      }

      console.log('📝 [PAGE] Sending to modal:', {
        agentData,
        mcp_configs: agentData.mcp_configs,
        firstConfig: agentData.mcp_configs[0],
        firstConfigTools: agentData.mcp_configs[0]?.tools
      })

      setSelectedAgent(agentData)
      setIsModalOpen(true)
    }
  }

  const handleCreate = () => {
    setSelectedAgent(undefined)
    setIsModalOpen(true)
  }

  const handleSave = async (agent: AgentFormData) => {
    try {
      // Extract avatar file if it's a File object
      const avatarFile = agent.avatar instanceof File ? agent.avatar : undefined

      if (agent.id) {
        // Update existing agent
        await updateAgent.mutateAsync({
          id: agent.id,
          data: {
            name: agent.name,
            system_prompt: agent.system_prompt,
            description: agent.description || null,
            tags: agent.tags || [],
            mcp_configs: (agent as any).mcp_configs || [],
            resources: (agent as any).resources || [],
          },
          avatar: avatarFile,
        })
      } else {
        // Create new agent
        await createAgent.mutateAsync({
          dto: {
            name: agent.name,
            system_prompt: agent.system_prompt,
            description: agent.description || null,
            tags: agent.tags || [],
            enabled: true,
            mcp_configs: (agent as any).mcp_configs || [],
            resources: (agent as any).resources || [],
          },
          avatar: avatarFile,
        })
      }

      setIsModalOpen(false)
      setSelectedAgent(undefined)
    } catch (error) {
      console.error("Failed to save agent:", error)

      const errorMessage = error instanceof Error ? error.message : "Échec de l'enregistrement"

      if (errorMessage.includes("duplicate key") || errorMessage.includes("already exists")) {
        toast.error("Un agent avec ce nom existe déjà. Veuillez choisir un autre nom.")
      } else {
        toast.error(extractErrorMessage(error))
      }
    }
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedAgent(undefined)
  }

  const handleDelete = (agentId: string) => {
    setAgentToDelete(agentId)
    setDeleteConfirmOpen(true)
  }

  const confirmDelete = async () => {
    if (!agentToDelete) return

    try {
      // Premier appel sans confirmation
      await deleteAgent.mutateAsync(agentToDelete)

      // Si succès direct (pas d'impact) → fermer
      setDeleteConfirmOpen(false)
      setAgentToDelete(null)
    } catch (error: any) {
      // Intercepter le 409 Conflict
      if (error.response?.status === 409 && error.response?.data?.detail?.type === 'confirmation_required') {
        // Fermer le dialog simple
        setDeleteConfirmOpen(false)

        // Afficher le dialog en cascade avec l'impact
        setDeleteImpact(error.response.data.detail.impact)
        setCascadeDialogOpen(true)
      } else {
        // Autre erreur → laisser le hook gérer
        throw error
      }
    }
  }

  const confirmCascadeDelete = async () => {
    if (!agentToDelete) return

    try {
      // Appel avec header de confirmation
      await deleteAgent.mutateAsync({
        id: agentToDelete,
        headers: { 'X-Confirm-Deletion': 'true' }
      })

      setCascadeDialogOpen(false)
      setDeleteImpact(null)
      setAgentToDelete(null)
    } catch (error) {
      console.error('Error force deleting agent:', error)
    }
  }

  const handleDuplicate = async (agentId: string) => {
    await duplicateAgent.mutateAsync(agentId)
  }

  const handleToggleAgent = async (agentId: string, enabled: boolean) => {
    await toggleAgent.mutateAsync({ id: agentId, enabled })
  }

  const handleCreateTeam = () => {
    setSelectedTeam(undefined)
    setIsTeamModalOpen(true)
  }

  const handleEditTeam = (teamId: string) => {
    const team = teams.find((t) => t.id === teamId)
    if (team) {
      setSelectedTeam(team)
      setIsTeamModalOpen(true)
    }
  }

  // Team handlers (kept as is with dynamic imports)
  const handleSaveTeam = async (team: Team) => {
    if (!userId) return

    try {
      const { createTeam, updateTeam } = await import("@/lib/api")

      if (team.id) {
        await updateTeam(team.id, team, userId)
        toast.success("Équipe mise à jour avec succès")
      } else {
        await createTeam(team, userId)
        toast.success("Équipe créée avec succès")
      }

      setIsTeamModalOpen(false)
      setSelectedTeam(undefined)

      // Reload teams
      const { getTeams } = await import("@/lib/api")
      const fetchedTeams = await getTeams(userId)
      setTeams(fetchedTeams)
    } catch (error) {
      console.error("Failed to save team:", error)
      toast.error("Échec de l'enregistrement de l'équipe")
    }
  }

  const handleDeleteTeam = (teamId: string) => {
    setTeamToDelete(teamId)
    setDeleteTeamConfirmOpen(true)
  }

  const confirmDeleteTeam = async () => {
    if (!userId || !teamToDelete) return

    try {
      const { deleteTeam, getTeams } = await import("@/lib/api")
      await deleteTeam(teamToDelete, userId)
      toast.success("Équipe supprimée avec succès")

      // Reload teams
      const fetchedTeams = await getTeams(userId)
      setTeams(fetchedTeams)
    } catch (error) {
      console.error("Failed to delete team:", error)
      toast.error("Échec de la suppression de l'équipe")
    } finally {
      setDeleteTeamConfirmOpen(false)
      setTeamToDelete(null)
    }
  }

  const handleDuplicateTeam = async (teamId: string) => {
    if (!userId) return

    try {
      const { duplicateTeam, getTeams } = await import("@/lib/api")
      await duplicateTeam(teamId, userId)
      toast.success("Équipe dupliquée avec succès")

      // Reload teams
      const fetchedTeams = await getTeams(userId)
      setTeams(fetchedTeams)
    } catch (error) {
      console.error("Failed to duplicate team:", error)
      toast.error("Échec de la duplication de l'équipe")
    }
  }

  const handleToggleTeam = async (teamId: string, enabled: boolean) => {
    if (!userId) return

    try {
      const { toggleTeam, getTeams } = await import("@/lib/api")
      await toggleTeam(teamId, enabled, userId)
      toast.success(enabled ? "Équipe activée" : "Équipe désactivée")

      // Reload teams
      const fetchedTeams = await getTeams(userId)
      setTeams(fetchedTeams)
    } catch (error) {
      console.error("Failed to toggle team:", error)
      toast.error("Échec du changement de statut de l'équipe")
    }
  }

  // Filter agents and teams based on search query
  const filteredAgents = agents.filter((agent) =>
    agent.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredTeams = teams.filter((team) =>
    team.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground mt-1">
            Gérez vos agents d'IA
          </p>
        </div>

        <div className="mb-6 flex items-center justify-between">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="icon" variant="ghost" disabled={isMutating}>
                <Plus className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleCreate}>
                <Bot className="size-4 mr-2" />
                Créer un agent
              </DropdownMenuItem>
              {/* Créer une équipe - TEMPORAIREMENT CACHÉ */}
              {false && (
                <DropdownMenuItem onClick={handleCreateTeam}>
                  <Users className="size-4 mr-2" />
                  Créer une équipe
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="mb-8">
          <div className="max-h-[600px] overflow-y-auto pr-2">
            {isLoadingAgents ? (
              <div className="flex items-center justify-center py-12">
                <div className="size-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredAgents.map((agent) => (
                    <AgentCard
                      key={agent.id}
                      id={agent.id}
                      name={agent.name}
                      description={agent.description || undefined}
                      avatar={(agent as any).avatar_url || undefined}
                      tags={agent.tags}
                      enabled={agent.enabled}
                      isSystem={agent.is_system}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                      onDuplicate={handleDuplicate}
                      onToggle={handleToggleAgent}
                    />
                  ))}
                </div>

                {filteredAgents.length === 0 && (
                  <div className="text-center py-12">
                    <p className="text-muted-foreground">
                      {searchQuery
                        ? "Aucun agent trouvé"
                        : "Aucun agent disponible"}
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Section Équipes - TEMPORAIREMENT CACHÉE (pas encore opérationnel) */}
        {false && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold tracking-tight mb-4">Équipes</h2>
            <div className="max-h-[600px] overflow-y-auto pr-2">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredTeams.map((team) => (
                  <TeamCard
                    key={team.id}
                    id={team.id}
                    name={team.name}
                    description={team.description}
                    tags={team.tags}
                    agentCount={team.agents.length}
                    enabled={team.enabled}
                    onEdit={handleEditTeam}
                    onDelete={handleDeleteTeam}
                    onDuplicate={handleDuplicateTeam}
                    onToggle={handleToggleTeam}
                  />
                ))}
              </div>

              {filteredTeams.length === 0 && (
                <div className="text-center py-12">
                  <p className="text-muted-foreground">
                    {searchQuery
                      ? "Aucune équipe trouvée"
                      : "Aucune équipe disponible"}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <AgentModal
        open={isModalOpen}
        onClose={handleCloseModal}
        agent={selectedAgent}
        onSave={handleSave}
        saving={createAgent.isPending || updateAgent.isPending}
      />

      <TeamModal
        open={isTeamModalOpen}
        onClose={() => {
          setIsTeamModalOpen(false)
          setSelectedTeam(undefined)
        }}
        team={selectedTeam}
        onSave={handleSaveTeam}
        saving={isMutating}
      />

      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title="Supprimer l'agent"
        description="Êtes-vous sûr de vouloir supprimer cet agent ? Cette action est irréversible."
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        onConfirm={confirmDelete}
        variant="destructive"
      />

      <CascadeConfirmDialog
        open={cascadeDialogOpen}
        onOpenChange={setCascadeDialogOpen}
        entityType="agent"
        entityName={deleteImpact?.agent_name || ""}
        impact={deleteImpact}
        onConfirm={confirmCascadeDelete}
        loading={deleteAgent.isPending}
      />

      <ConfirmDialog
        open={deleteTeamConfirmOpen}
        onOpenChange={setDeleteTeamConfirmOpen}
        title="Supprimer l'équipe"
        description="Êtes-vous sûr de vouloir supprimer cette équipe ? Les agents ne seront pas supprimés."
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        onConfirm={confirmDeleteTeam}
        variant="destructive"
      />
    </AppLayout>
  )
}
