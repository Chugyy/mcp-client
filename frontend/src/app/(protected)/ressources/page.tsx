"use client"

import { useState } from "react"
import { Search, Plus } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ResourceCard } from "@/components/resources/card"
import { ResourceModal } from "@/components/resources/modal"
import { ConfirmDialog } from "@/components/ui/confirm-dialog"
import { CascadeConfirmDialog } from "@/components/ui/cascade-confirm-dialog"
import { AppLayout } from "@/components/layouts/app-layout"
import { ResourceWithUploads, Resource, Upload } from "@/lib/api"
import {
  useResources,
  useCreateResource,
  useUpdateResource,
  useDeleteResource,
  useIngestResource,
  useUploadFile,
  useDeleteUpload,
  useResource,
  useResourceUploads,
} from "@/services/resources/resources.hooks"

export default function ResourcesPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedResourceId, setSelectedResourceId] = useState<string | undefined>()
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [resourceToDelete, setResourceToDelete] = useState<string | null>(null)
  const [cascadeDialogOpen, setCascadeDialogOpen] = useState(false)
  const [deleteImpact, setDeleteImpact] = useState<any>(null)

  // Fetch resources avec React Query
  const { data: resourcesData = [], isLoading, error } = useResources()

  // Convertir les resources du service en type Resource de l'API
  const resources: Resource[] = resourcesData.map((r) => ({
    ...r,
    status: r.status as 'pending' | 'processing' | 'ready' | 'error',
  }))

  // Fetch detailed resource with uploads when editing
  const { data: selectedResourceDetailData } = useResource(selectedResourceId || "")
  const { data: selectedResourceUploadsData = [] } = useResourceUploads(selectedResourceId || "")

  // Convertir en types API et construire le ResourceWithUploads pour le modal
  const selectedResource: ResourceWithUploads | undefined =
    selectedResourceDetailData && selectedResourceId
      ? {
          ...selectedResourceDetailData,
          status: selectedResourceDetailData.status as 'pending' | 'processing' | 'ready' | 'error',
          uploads: selectedResourceUploadsData.map((u): Upload => ({
            id: u.id,
            resource_id: u.resource_id,
            filename: u.filename,
            file_path: u.file_path,
            file_size: u.file_size ?? 0,
            mime_type: u.mime_type ?? 'application/octet-stream',
            type: u.type as 'avatar' | 'document' | 'resource',
            created_at: u.created_at,
          })),
        }
      : undefined

  // Hooks pour les mutations
  const createResource = useCreateResource()
  const updateResource = useUpdateResource()
  const deleteResource = useDeleteResource()
  const ingestResource = useIngestResource()
  const uploadFile = useUploadFile()
  const deleteUpload = useDeleteUpload()

  // Calculer l'état saving basé sur les mutations en cours
  const saving = createResource.isPending || updateResource.isPending || uploadFile.isPending

  const handleCreate = () => {
    setSelectedResourceId(undefined)
    setIsModalOpen(true)
  }

  const handleEdit = (resourceId: string) => {
    setSelectedResourceId(resourceId)
    setIsModalOpen(true)
  }

  const handleSave = async (data: {
    name: string
    description?: string | null
    files?: File[]
  }) => {
    try {
      if (selectedResource) {
        // Mode édition
        await updateResource.mutateAsync({
          id: selectedResource.id,
          data: {
            name: data.name,
            description: data.description || null,
          },
        })

        // Upload des fichiers ajoutés (si présents)
        if (data.files && data.files.length > 0) {
          await Promise.all(
            data.files.map((file) =>
              uploadFile.mutateAsync({
                resourceId: selectedResource.id,
                file,
              })
            )
          )

          // Réindexer la ressource après ajout de fichiers
          ingestResource.mutate(selectedResource.id)
        }
      } else {
        // Mode création
        const createdResource = await createResource.mutateAsync({
          name: data.name,
          description: data.description || null,
          enabled: true, // Toujours activé par défaut
        })

        // Upload des fichiers si présents
        if (data.files && data.files.length > 0) {
          await Promise.all(
            data.files.map((file) =>
              uploadFile.mutateAsync({
                resourceId: createdResource.id,
                file,
              })
            )
          )

          // Déclencher l'ingestion automatiquement après upload
          ingestResource.mutate(createdResource.id)
        }
      }

      // Fermer la modale immédiatement
      setIsModalOpen(false)
      setSelectedResourceId(undefined)
    } catch (error) {
      console.error("Failed to save resource:", error)
      // Les erreurs sont gérées par les hooks avec toast
    }
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedResourceId(undefined)
  }

  const handleDelete = (resourceId: string) => {
    setResourceToDelete(resourceId)
    setDeleteConfirmOpen(true)
  }

  const confirmDelete = async () => {
    if (!resourceToDelete) return

    try {
      // Premier appel sans confirmation
      await deleteResource.mutateAsync(resourceToDelete)

      // Si succès direct (pas d'impact) → fermer
      setDeleteConfirmOpen(false)
      setResourceToDelete(null)
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
        console.error("Failed to delete resource:", error)
      }
    }
  }

  const confirmCascadeDelete = async () => {
    if (!resourceToDelete) return

    try {
      // Appel avec header de confirmation
      await deleteResource.mutateAsync({
        id: resourceToDelete,
        headers: { 'X-Confirm-Deletion': 'true' }
      })

      setCascadeDialogOpen(false)
      setDeleteImpact(null)
      setResourceToDelete(null)
    } catch (error) {
      console.error('Error force deleting resource:', error)
    }
  }

  const handleDeleteUpload = async (uploadId: string, resourceId: string) => {
    try {
      await deleteUpload.mutateAsync(uploadId)

      // Réindexer la ressource après suppression de fichier
      // (le backend gérera la suppression des embeddings)
      ingestResource.mutate(resourceId)
    } catch (error) {
      console.error("Failed to delete upload:", error)
      // Les erreurs sont gérées par le hook avec toast
    }
  }

  // Ajouter uploads vides pour la liste (les uploads réels sont chargés dans le modal uniquement)
  const resourcesWithUploads: ResourceWithUploads[] = resources.map((r) => ({
    ...r,
    uploads: [],
  }))

  const filteredResources = resourcesWithUploads.filter((resource) =>
    resource.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Ressources</h1>
          <p className="text-muted-foreground mt-1">
            Gérez vos ressources RAG pour alimenter vos agents avec des connaissances
          </p>
        </div>

        {saving && (
          <div className="flex items-center justify-center gap-2 mb-6 p-4 bg-muted rounded-lg">
            <div className="size-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-muted-foreground">Enregistrement...</p>
          </div>
        )}

        <div className="mb-6 flex items-center justify-between">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher une ressource..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button size="icon" variant="ghost" onClick={handleCreate} disabled={saving}>
            <Plus className="size-4" />
          </Button>
        </div>

        <div className="mb-8">
          <div className="max-h-[600px] overflow-y-auto pr-2">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredResources.map((resource) => (
                <ResourceCard
                  key={resource.id}
                  resource={resource}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                />
              ))}
            </div>

            {filteredResources.length === 0 && (
              <div className="text-center py-12">
                <p className="text-muted-foreground">
                  {searchQuery
                    ? "Aucune ressource trouvée"
                    : "Aucune ressource disponible"}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <ResourceModal
        open={isModalOpen}
        onClose={handleCloseModal}
        resource={selectedResource}
        onSave={handleSave}
        onDeleteUpload={handleDeleteUpload}
        saving={saving}
      />

      <ConfirmDialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title="Supprimer la ressource"
        description="Êtes-vous sûr de vouloir supprimer cette ressource ? Tous les fichiers et embeddings associés seront supprimés définitivement."
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        onConfirm={confirmDelete}
        variant="destructive"
      />

      <CascadeConfirmDialog
        open={cascadeDialogOpen}
        onOpenChange={setCascadeDialogOpen}
        entityType="resource"
        entityName={resources.find(r => r.id === resourceToDelete)?.name || ""}
        impact={deleteImpact}
        onConfirm={confirmCascadeDelete}
        loading={deleteResource.isPending}
      />
    </AppLayout>
  )
}
