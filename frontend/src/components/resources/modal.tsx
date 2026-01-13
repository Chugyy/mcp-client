"use client"

import { useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { AlertCircleIcon, FileUpIcon, XIcon, Trash2 } from "lucide-react"
import { ResourceWithUploads, Upload } from "@/lib/api"
import { useFileUpload, formatBytes } from "@/hooks/use-file-upload"
import { getFileIcon } from "@/lib/file-utils"

interface ResourceModalProps {
  open: boolean
  onClose: () => void
  resource?: ResourceWithUploads
  onSave?: (data: {
    name: string
    description?: string | null
    files?: File[]
  }) => void
  onDeleteUpload?: (uploadId: string, resourceId: string) => void
  saving?: boolean
}

export function ResourceModal({
  open,
  onClose,
  resource,
  onSave,
  onDeleteUpload,
  saving = false,
}: ResourceModalProps) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")

  const maxSize = 10 * 1024 * 1024 // 10 MB (conforme backend)
  const acceptedTypes = ".pdf,.png,.jpg,.jpeg,.doc,.docx,.txt"

  const [
    { files, isDragging, errors },
    {
      handleDragEnter,
      handleDragLeave,
      handleDragOver,
      handleDrop,
      openFileDialog,
      removeFile,
      clearFiles,
      getInputProps,
    },
  ] = useFileUpload({
    maxFiles: 10, // Support multi-fichiers
    maxSize,
    accept: acceptedTypes,
    multiple: true, // Activer multi-sélection
  })

  useEffect(() => {
    if (open) {
      if (resource) {
        // Mode édition : pré-remplir avec les données existantes
        setName(resource.name || "")
        setDescription(resource.description || "")
        clearFiles()
      } else {
        // Mode création : réinitialiser
        setName("")
        setDescription("")
        clearFiles()
      }
    }
  }, [open, resource])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!name.trim()) {
      return // Nom requis
    }

    if (!resource && files.length === 0) {
      return // Au moins un fichier requis en mode création
    }

    const filesList = files
      .map((f) => (f.file instanceof File ? f.file : null))
      .filter((f): f is File => f !== null)

    onSave?.({
      name: name.trim(),
      description: description.trim() || null,
      files: filesList.length > 0 ? filesList : undefined,
    })
  }

  const FileIcon = files.length > 0 && files[0].file instanceof File
    ? getFileIcon(files[0].file.type, files[0].file.name)
    : null

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {resource ? "Modifier la ressource" : "Créer une ressource"}
          </DialogTitle>
          <DialogDescription>
            {resource
              ? "Modifiez les métadonnées et gérez les fichiers de la ressource"
              : "Créez une nouvelle ressource RAG avec vos fichiers"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Nom de la ressource */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Nom de la ressource <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex: Documentation Q4 2024"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brève description de cette ressource..."
              rows={3}
            />
          </div>

          {/* Fichiers actuels (mode édition) */}
          {resource && resource.uploads.length > 0 && (
            <div className="space-y-2">
              <Label>Fichiers actuels ({resource.uploads.length})</Label>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {resource.uploads.map((upload) => {
                  const Icon = getFileIcon(upload.mime_type, upload.filename)
                  return (
                    <div
                      key={upload.id}
                      className="flex items-center justify-between gap-2 rounded-lg border bg-background p-2"
                    >
                      <div className="flex items-center gap-3 overflow-hidden flex-1">
                        <div className="flex aspect-square size-10 shrink-0 items-center justify-center rounded border">
                          <Icon className="size-4 opacity-60" />
                        </div>
                        <div className="flex min-w-0 flex-col gap-0.5">
                          <p className="truncate font-medium text-[13px]">
                            {upload.filename}
                          </p>
                          <p className="text-muted-foreground text-xs">
                            {formatBytes(upload.file_size)}
                          </p>
                        </div>
                      </div>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="size-8 text-destructive hover:text-destructive"
                        onClick={() => onDeleteUpload?.(upload.id, resource.id)}
                        type="button"
                        title="Supprimer ce fichier"
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Zone d'upload */}
          <div className="space-y-2">
            <Label>
              {resource ? "Ajouter des fichiers" : "Fichiers"}{" "}
              {!resource && <span className="text-destructive">*</span>}
            </Label>

            {/* Zone de drop */}
            <div
              className="flex min-h-32 flex-col items-center justify-center rounded-xl border border-input border-dashed p-4 transition-colors hover:bg-accent/50 has-disabled:pointer-events-none has-[input:focus]:border-ring has-disabled:opacity-50 has-[input:focus]:ring-[3px] has-[input:focus]:ring-ring/50 data-[dragging=true]:bg-accent/50 cursor-pointer"
              data-dragging={isDragging || undefined}
              onClick={openFileDialog}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              role="button"
              tabIndex={-1}
            >
              <input
                {...getInputProps()}
                aria-label="Upload files"
                className="sr-only"
              />

              <div className="flex flex-col items-center justify-center text-center">
                <div
                  aria-hidden="true"
                  className="mb-2 flex size-11 shrink-0 items-center justify-center rounded-full border bg-background"
                >
                  <FileUpIcon className="size-4 opacity-60" />
                </div>
                <p className="mb-1.5 font-medium text-sm">
                  Glissez vos fichiers ici
                </p>
                <p className="mb-2 text-muted-foreground text-xs">
                  ou cliquez pour parcourir
                </p>
                <div className="flex flex-wrap justify-center gap-1 text-muted-foreground/70 text-xs">
                  <span>PDF, PNG, JPG, DOC, TXT</span>
                  <span>∙</span>
                  <span>Max 10 fichiers</span>
                  <span>∙</span>
                  <span>{formatBytes(maxSize)} par fichier</span>
                </div>
              </div>
            </div>

            {/* Erreurs */}
            {errors.length > 0 && (
              <div
                className="flex items-center gap-1 text-destructive text-xs"
                role="alert"
              >
                <AlertCircleIcon className="size-3 shrink-0" />
                <span>{errors[0]}</span>
              </div>
            )}

            {/* Fichiers sélectionnés */}
            {files.length > 0 && (
              <div className="space-y-2">
                {files.map((file) => {
                  const Icon = getFileIcon(
                    file.file instanceof File ? file.file.type : file.file.type,
                    file.file instanceof File ? file.file.name : file.file.name
                  )
                  return (
                    <div
                      key={file.id}
                      className="flex items-center justify-between gap-2 rounded-lg border bg-background p-2 pe-3"
                    >
                      <div className="flex items-center gap-3 overflow-hidden">
                        <div className="flex aspect-square size-10 shrink-0 items-center justify-center rounded border">
                          <Icon className="size-4 opacity-60" />
                        </div>
                        <div className="flex min-w-0 flex-col gap-0.5">
                          <p className="truncate font-medium text-[13px]">
                            {file.file instanceof File
                              ? file.file.name
                              : file.file.name}
                          </p>
                          <p className="text-muted-foreground text-xs">
                            {formatBytes(
                              file.file instanceof File
                                ? file.file.size
                                : file.file.size
                            )}
                          </p>
                        </div>
                      </div>

                      <Button
                        aria-label="Remove file"
                        className="-me-2 size-8 text-muted-foreground/80 hover:bg-transparent hover:text-foreground"
                        onClick={() => removeFile(file.id)}
                        size="icon"
                        variant="ghost"
                        type="button"
                      >
                        <XIcon aria-hidden="true" className="size-4" />
                      </Button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Annuler
            </Button>
            <Button
              type="submit"
              disabled={
                saving ||
                !name.trim() ||
                (!resource && files.length === 0)
              }
            >
              {saving ? (
                <>
                  <div className="size-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
                  {resource ? "Enregistrement..." : "Création..."}
                </>
              ) : (
                resource ? "Enregistrer" : "Créer"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
