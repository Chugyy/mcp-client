"use client"

import { useState } from "react"
import { Search, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { MCPCard } from "@/components/mcp/card"
import { MCPModal } from "@/components/mcp/modal"
import { ConfirmDialog } from "@/components/ui/confirm-dialog"
import { CascadeConfirmDialog } from "@/components/ui/cascade-confirm-dialog"
import { AppLayout } from "@/components/layouts/app-layout"
import {
  useMCPServers,
  useCreateMCPServer,
  useUpdateMCPServer,
  useDeleteMCPServer,
  useSyncMCPServer,
} from '@/services/mcp/mcp.hooks'
import type { CreateMCPServerDTO, UpdateMCPServerDTO, MCPServerWithTools, MCPServerType } from '@/services/mcp/mcp.types'
import { toast } from "sonner"

// Type pour le modal (format camelCase)
interface MCPModalData {
  id?: string
  name: string
  description?: string
  type: MCPServerType

  // HTTP
  url?: string
  authType?: "api-key" | "oauth" | "none"
  apiKeyValue?: string

  // Stdio
  args?: string[]
  env?: Record<string, string>

  enabled?: boolean
}

export default function MCPToolsPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedMCP, setSelectedMCP] = useState<MCPServerWithTools | undefined>()
  const [selectedModalMCP, setSelectedModalMCP] = useState<MCPModalData | undefined>()
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [mcpToDelete, setMCPToDelete] = useState<string | null>(null)
  const [cascadeDialogOpen, setCascadeDialogOpen] = useState(false)
  const [deleteImpact, setDeleteImpact] = useState<any>(null)

  const { data: mcpServers = [], isLoading, error } = useMCPServers({ with_tools: true }) as {
    data: MCPServerWithTools[]
    isLoading: boolean
    error: Error | null
  }
  const createMCP = useCreateMCPServer()
  const updateMCP = useUpdateMCPServer()
  const deleteMCP = useDeleteMCPServer()
  const syncMCP = useSyncMCPServer()

  const handleCreate = () => {
    setSelectedMCP(undefined)
    setSelectedModalMCP(undefined)
    setIsModalOpen(true)
  }

  const handleEdit = (mcpId: string) => {
    const mcp = mcpServers.find((m) => m.id === mcpId)
    if (mcp) {
      // Conversion du format backend vers le format modal
      const modalMCP: MCPModalData = {
        id: mcp.id,
        name: mcp.name,
        description: mcp.description ?? undefined,
        type: mcp.type,

        // HTTP fields
        url: mcp.url ?? undefined,
        authType: mcp.auth_type ?? undefined,
        apiKeyValue: undefined, // Never sent back by API

        // Stdio fields
        args: mcp.args ?? undefined,
        env: {}, // Never sent back by API (security)

        enabled: mcp.enabled,
      }
      setSelectedMCP(mcp)
      setSelectedModalMCP(modalMCP)
      setIsModalOpen(true)
    }
  }

  const handleSave = async (modalData: MCPModalData) => {
    try {
      // Conversion du format modal (camelCase) vers le format backend (snake_case)
      const backendData: Partial<CreateMCPServerDTO> = {
        name: modalData.name,
        description: modalData.description || null,
        type: modalData.type,
        enabled: modalData.enabled ?? true,
      }

      // HTTP-specific fields
      if (modalData.type === 'http') {
        backendData.url = modalData.url || null
        backendData.auth_type = modalData.authType || null
        backendData.api_key_value = modalData.apiKeyValue || null
      }

      // Stdio-specific fields (npx, uvx, docker)
      if (modalData.type !== 'http') {
        // Filter out empty args
        backendData.args = (modalData.args || []).filter(arg => arg.trim() !== '')

        // Filter out empty env keys/values
        const cleanedEnv: Record<string, string> = {}
        Object.entries(modalData.env || {}).forEach(([key, value]) => {
          if (key.trim() !== '' && value.trim() !== '') {
            cleanedEnv[key] = value
          }
        })
        backendData.env = Object.keys(cleanedEnv).length > 0 ? cleanedEnv : null
      }

      if (selectedMCP?.id) {
        // Mode édition
        await updateMCP.mutateAsync({ id: selectedMCP.id, data: backendData as UpdateMCPServerDTO })
      } else {
        // Mode création
        await createMCP.mutateAsync(backendData as CreateMCPServerDTO)
      }
      setIsModalOpen(false)
      setSelectedMCP(undefined)
      setSelectedModalMCP(undefined)
    } catch (error) {
      // Les erreurs sont déjà gérées par les hooks (toast)
      console.error('Error saving MCP server:', error)
    }
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedMCP(undefined)
    setSelectedModalMCP(undefined)
  }

  const handleBulkImport = async (servers: MCPModalData[]) => {
    try {
      // Préparer les promesses pour tous les serveurs (parallélisation)
      const promises = servers.map(async (server) => {
        // Validation du name
        if (!server.name || server.name.trim() === '') {
          throw new Error(`Nom vide`)
        }

        // Filtrer les args vides
        const cleanArgs = (server.args || []).filter(arg => arg.trim() !== '')

        // Validation des args pour stdio
        if (server.type !== 'http' && cleanArgs.length === 0) {
          throw new Error(`Args vide pour ${server.type}`)
        }

        const backendData: CreateMCPServerDTO = {
          name: server.name.trim(),
          description: server.description || null,
          type: server.type,
          args: cleanArgs,
          env: server.env || {},
          enabled: true,
        }

        await createMCP.mutateAsync(backendData)
        return { success: true, name: server.name }
      })

      // Exécuter toutes les promesses en parallèle
      const results = await Promise.allSettled(promises)

      // Compter les succès et afficher les erreurs détaillées
      let successCount = 0
      let errorCount = 0

      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          successCount++
        } else {
          errorCount++
          const serverName = servers[index].name || `Serveur #${index + 1}`
          const errorMessage = result.reason?.message || 'Erreur inconnue'
          toast.error(`${serverName}: ${errorMessage}`)
        }
      })

      if (successCount > 0) {
        toast.success(`${successCount} serveur${successCount > 1 ? 's' : ''} importé${successCount > 1 ? 's' : ''} avec succès`)
      }

      setIsModalOpen(false)
      setSelectedMCP(undefined)
      setSelectedModalMCP(undefined)
    } catch (error) {
      console.error('Error bulk importing MCP servers:', error)
      toast.error('Erreur lors de l\'import des serveurs')
    }
  }


  const handleDelete = (mcpId: string) => {
    setMCPToDelete(mcpId)
    setDeleteConfirmOpen(true)
  }

  const confirmDelete = async () => {
    if (!mcpToDelete) return

    try {
      // Premier appel sans confirmation
      await deleteMCP.mutateAsync(mcpToDelete)

      // Si succès direct (pas d'impact) → fermer
      setDeleteConfirmOpen(false)
      setMCPToDelete(null)
    } catch (error: any) {
      // Intercepter le 409 Conflict
      if (error.response?.status === 409 && error.response?.data?.detail?.type === 'confirmation_required') {
        // Fermer le dialog simple
        setDeleteConfirmOpen(false)

        // Afficher le dialog en cascade avec l'impact
        setDeleteImpact(error.response.data.detail.impact)
        setCascadeDialogOpen(true)
      } else {
        // Autre erreur → déjà gérée par le hook
        console.error('Error deleting MCP server:', error)
      }
    }
  }

  const confirmCascadeDelete = async () => {
    if (!mcpToDelete) return

    try {
      // Appel avec header de confirmation
      await deleteMCP.mutateAsync({
        id: mcpToDelete,
        headers: { 'X-Confirm-Deletion': 'true' }
      })

      setCascadeDialogOpen(false)
      setDeleteImpact(null)
      setMCPToDelete(null)
    } catch (error) {
      console.error('Error force deleting MCP server:', error)
    }
  }

  const handleToggleMCP = async (mcpId: string, enabled: boolean) => {
    try {
      await updateMCP.mutateAsync({ id: mcpId, data: { enabled } })
    } catch (error) {
      console.error('Error toggling MCP server:', error)
    }
  }

  const handleSync = async (mcpId: string) => {
    try {
      await syncMCP.mutateAsync(mcpId)
    } catch (error) {
      console.error('Error syncing MCP server:', error)
    }
  }

  const filteredMCPs = mcpServers.filter((mcp) =>
    mcp.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (isLoading) {
    return (
      <AppLayout>
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          <div className="flex items-center justify-center gap-2 p-8">
            <div className="size-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-muted-foreground">Chargement des serveurs MCP...</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  if (error) {
    return (
      <AppLayout>
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          <div className="p-4 bg-destructive/10 text-destructive rounded-lg">
            <p>Erreur lors du chargement des serveurs MCP</p>
            <p className="text-sm mt-1">{error.message}</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Serveurs MCP</h1>
          <p className="text-muted-foreground mt-1">
            Gérez vos serveurs Model Context Protocol
          </p>
        </div>

        <div className="mb-6 flex items-center justify-between">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher un serveur MCP..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button size="sm" onClick={handleCreate} disabled={createMCP.isPending || updateMCP.isPending}>
            <Plus className="size-4 mr-2" />
            Nouveau serveur
          </Button>
        </div>

        <div className="mb-8">
          <div className="max-h-[600px] overflow-y-auto pr-2">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredMCPs.map((mcp) => (
                <MCPCard
                  key={mcp.id}
                  id={mcp.id}
                  name={mcp.name}
                  description={mcp.description ?? undefined}
                  type={mcp.type}
                  url={mcp.url}
                  args={mcp.args}
                  authType={mcp.auth_type}
                  enabled={mcp.enabled}
                  status={mcp.status}
                  statusMessage={mcp.status_message ?? undefined}
                  stale={mcp.stale}
                  isSystem={mcp.is_system}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onToggle={handleToggleMCP}
                  onSync={handleSync}
                />
              ))}
            </div>

            {filteredMCPs.length === 0 && (
              <div className="text-center py-12">
                <p className="text-muted-foreground">
                  {searchQuery
                    ? "Aucun serveur MCP trouvé"
                    : "Aucun serveur MCP disponible"}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <MCPModal
        open={isModalOpen}
        onClose={handleCloseModal}
        mcp={selectedModalMCP}
        onSave={handleSave}
        onBulkImport={handleBulkImport}
        saving={createMCP.isPending || updateMCP.isPending}
      />

      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title="Supprimer le serveur MCP"
        description="Êtes-vous sûr de vouloir supprimer ce serveur MCP ? Cette action est irréversible."
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        onConfirm={confirmDelete}
        variant="destructive"
      />

      <CascadeConfirmDialog
        open={cascadeDialogOpen}
        onOpenChange={setCascadeDialogOpen}
        entityType="server"
        entityName={mcpServers.find(m => m.id === mcpToDelete)?.name || ""}
        impact={deleteImpact}
        onConfirm={confirmCascadeDelete}
        loading={deleteMCP.isPending}
      />
    </AppLayout>
  )
}
