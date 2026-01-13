"use client"

import { CircleUserRoundIcon, XIcon } from "lucide-react"
import { useFileUpload } from "@/hooks/use-file-upload"
import { Button } from "@/components/ui/button"
import { useUploadBlobUrl } from "@/services/uploads/uploads.hooks"

interface AvatarUploadProps {
  onFileChange?: (file: File | null) => void
  onFilePickerOpen?: () => void
  defaultUploadId?: string // Upload ID from backend
}

export function AvatarUpload({ onFileChange, onFilePickerOpen, defaultUploadId }: AvatarUploadProps) {
  const [{ files }, { removeFile, openFileDialog, getInputProps }] =
    useFileUpload({
      accept: "image/*",
      onFilesChange: (files) => {
        const file = files[0]?.file instanceof File ? files[0].file : null
        onFileChange?.(file)
      },
    })

  const handleOpenFileDialog = () => {
    onFilePickerOpen?.()
    openFileDialog()
  }

  // Fetch blob URL for existing avatar
  const { data: existingAvatarUrl } = useUploadBlobUrl(defaultUploadId)

  const previewUrl = files[0]?.preview || existingAvatarUrl || null
  const fileName = files[0]?.file.name || null

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative inline-flex">
        <Button
          type="button"
          variant="outline"
          className="relative size-16 overflow-hidden p-0 shadow-none"
          onClick={handleOpenFileDialog}
          aria-label={previewUrl ? "Change image" : "Upload image"}
        >
          {previewUrl ? (
            <img
              className="size-full object-cover"
              src={previewUrl}
              alt="Preview of uploaded image"
              width={64}
              height={64}
              style={{ objectFit: "cover" }}
            />
          ) : (
            <div aria-hidden="true">
              <CircleUserRoundIcon className="size-4 opacity-60" />
            </div>
          )}
        </Button>
        {previewUrl && (
          <Button
            type="button"
            onClick={() => removeFile(files[0]?.id)}
            size="icon"
            className="absolute -top-2 -right-2 size-6 rounded-full border-2 border-background shadow-none focus-visible:border-background"
            aria-label="Remove image"
          >
            <XIcon className="size-3.5" />
          </Button>
        )}
        <input
          {...getInputProps()}
          className="sr-only"
          aria-label="Upload image file"
          tabIndex={-1}
        />
      </div>
      {fileName && <p className="text-xs text-muted-foreground">{fileName}</p>}
    </div>
  )
}
