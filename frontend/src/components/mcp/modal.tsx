"use client"

import { useEffect, useState } from "react"
import { Plus, Trash2, HelpCircle } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { ServerTypeSelector } from "./server-type-selector"
import { JSONImportFlow } from "./json-import-flow"
import type { MCPServerType } from "@/services/mcp/mcp.types"
import { SERVER_TYPES } from "@/services/mcp/mcp.constants"

interface MCPServer {
  id?: string
  name: string
  description?: string
  type: MCPServerType

  // HTTP fields
  url?: string
  authType?: "api-key" | "oauth" | "none"
  apiKeyValue?: string

  // Stdio fields (npx, uvx, docker)
  args?: string[]
  env?: Record<string, string>

  enabled?: boolean
}

interface MCPModalProps {
  open: boolean
  onClose: () => void
  mcp?: MCPServer
  onSave?: (mcp: MCPServer) => void
  onBulkImport?: (servers: MCPServer[]) => void
  saving?: boolean
}

export function MCPModal({ open, onClose, mcp, onSave, onBulkImport, saving = false }: MCPModalProps) {
  const [formData, setFormData] = useState<MCPServer>({
    name: "",
    description: "",
    type: "http",
    url: "",
    authType: "api-key",
    apiKeyValue: "",
    args: [],
    env: {},
  })

  const [activeTab, setActiveTab] = useState<"manual" | "json">("manual")

  // Sync formData with mcp prop
  useEffect(() => {
    if (open) {
      if (mcp) {
        setFormData({
          id: mcp.id,
          name: mcp.name || "",
          description: mcp.description || "",
          type: mcp.type || "http",
          url: mcp.url || "",
          authType: mcp.authType || "api-key",
          apiKeyValue: mcp.apiKeyValue || "",
          args: mcp.args || [],
          env: mcp.env || {},
        })
      } else {
        setFormData({
          name: "",
          description: "",
          type: "http",
          url: "",
          authType: "api-key",
          apiKeyValue: "",
          args: [],
          env: {},
        })
      }
      setActiveTab("manual")
    }
  }, [open, mcp])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave?.(formData)
  }

  const handleTypeChange = (type: MCPServerType) => {
    setFormData({
      ...formData,
      type,
      // Reset type-specific fields
      url: type === 'http' ? formData.url : "",
      authType: type === 'http' ? formData.authType : undefined,
      apiKeyValue: type === 'http' ? formData.apiKeyValue : "",
      args: type !== 'http' ? formData.args : [],
      env: type !== 'http' ? formData.env : {},
    })
  }

  // Args management
  const addArg = () => {
    setFormData({
      ...formData,
      args: [...(formData.args || []), ""]
    })
  }

  const updateArg = (index: number, value: string) => {
    const newArgs = [...(formData.args || [])]
    newArgs[index] = value
    setFormData({ ...formData, args: newArgs })
  }

  const removeArg = (index: number) => {
    const newArgs = [...(formData.args || [])]
    newArgs.splice(index, 1)
    setFormData({ ...formData, args: newArgs })
  }

  // Env management
  const addEnvVar = () => {
    setFormData({
      ...formData,
      env: { ...(formData.env || {}), "": "" }
    })
  }

  const updateEnvKey = (oldKey: string, newKey: string) => {
    const newEnv = { ...(formData.env || {}) }
    const value = newEnv[oldKey]
    delete newEnv[oldKey]
    newEnv[newKey] = value
    setFormData({ ...formData, env: newEnv })
  }

  const updateEnvValue = (key: string, value: string) => {
    setFormData({
      ...formData,
      env: { ...(formData.env || {}), [key]: value }
    })
  }

  const removeEnvVar = (key: string) => {
    const newEnv = { ...(formData.env || {}) }
    delete newEnv[key]
    setFormData({ ...formData, env: newEnv })
  }

  const handleJSONImport = (servers: any[]) => {
    // LOG #4 - Réception depuis JSONImportFlow
    console.log('🔸 [MODAL] Received servers from JSONImportFlow:', servers.map(s => ({
      name: s.name,
      type: s.type,
      args: s.args,
      argsLength: s.args?.length
    })))

    const mappedServers: MCPServer[] = servers.map(s => ({
      name: s.name || '',
      description: s.description || undefined,
      type: s.type,
      args: s.args || [],
      env: s.env || {},
      enabled: true
    }))

    // LOG #5 - Mapping pour onBulkImport
    console.log('🔸 [MODAL] Mapped servers for onBulkImport:', mappedServers.map(s => ({
      name: s.name,
      nameEmpty: s.name === '',
      type: s.type,
      args: s.args,
      argsLength: s.args?.length,
      argsEmpty: s.args?.length === 0
    })))

    onBulkImport?.(mappedServers)

    // Fermer la modale après l'import
    onClose()
  }

  const typeConfig = SERVER_TYPES[formData.type]

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mcp ? "Modifier le serveur MCP" : "Créer un serveur MCP"}
          </DialogTitle>
          <DialogDescription>
            {mcp
              ? "Modifiez les informations du serveur MCP"
              : "Remplissez les détails pour créer un nouveau serveur MCP"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Server Type Selector */}
          <div className="space-y-2">
            <Label htmlFor="type">
              Type de serveur <span className="text-destructive">*</span>
            </Label>
            <ServerTypeSelector value={formData.type} onChange={handleTypeChange} />
            <p className="text-xs text-muted-foreground">{typeConfig.description}</p>
            {typeConfig.prerequisite && (
              <p className="text-xs text-yellow-600 dark:text-yellow-400">
                Prérequis : {typeConfig.prerequisite}
              </p>
            )}
          </div>

          {/* HTTP-specific fields */}
          {formData.type === 'http' && (
            <>
              {/* Name */}
              <div className="space-y-2">
                <Label htmlFor="name">
                  Nom <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="name"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="Nom du serveur MCP"
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="Brève description du serveur MCP"
                  rows={2}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="url">
                  URL du serveur <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="url"
                  required
                  type="url"
                  value={formData.url}
                  onChange={(e) =>
                    setFormData({ ...formData, url: e.target.value })
                  }
                  placeholder="https://api.example.com/mcp"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="authType">
                  Type d'authentification <span className="text-destructive">*</span>
                </Label>
                <Select
                  value={formData.authType}
                  onValueChange={(value: "api-key" | "oauth" | "none") =>
                    setFormData({ ...formData, authType: value, apiKeyValue: "" })
                  }
                >
                  <SelectTrigger id="authType">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="api-key">Clé API</SelectItem>
                    <SelectItem value="oauth">OAuth</SelectItem>
                    <SelectItem value="none">Sans authentification</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {formData.authType === "api-key" && (
                <div className="space-y-2">
                  <Label htmlFor="apiKeyValue">
                    Clé API <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="apiKeyValue"
                    required
                    type="password"
                    value={formData.apiKeyValue}
                    onChange={(e) =>
                      setFormData({ ...formData, apiKeyValue: e.target.value })
                    }
                    placeholder="Entrez votre clé API"
                  />
                  <p className="text-xs text-muted-foreground">
                    Le service sera créé automatiquement à partir du nom du serveur
                  </p>
                </div>
              )}
            </>
          )}

          {/* Stdio fields with Tabs (npx, uvx, docker) */}
          {formData.type !== 'http' && (
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "manual" | "json")}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="manual">Manuel</TabsTrigger>
                <TabsTrigger value="json">Import JSON</TabsTrigger>
              </TabsList>

              {/* Manual Tab */}
              <TabsContent value="manual" className="space-y-4 mt-4">
                {/* Name */}
                <div className="space-y-2">
                  <Label htmlFor="name-manual">
                    Nom <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="name-manual"
                    required
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    placeholder="Nom du serveur MCP"
                  />
                </div>

                {/* Description */}
                <div className="space-y-2">
                  <Label htmlFor="description-manual">Description</Label>
                  <Textarea
                    id="description-manual"
                    value={formData.description}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    placeholder="Brève description du serveur MCP"
                    rows={2}
                  />
                </div>

                {/* Arguments */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Label>
                      Arguments <span className="text-destructive">*</span>
                    </Label>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            {typeConfig.argsPlaceholder && `Exemple : ${typeConfig.argsPlaceholder}`}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>

                  <div className="space-y-2">
                    {formData.args?.map((arg, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <Input
                          value={arg}
                          onChange={(e) => updateArg(index, e.target.value)}
                          placeholder={`Argument ${index + 1}`}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeArg(index)}
                          className="flex-shrink-0"
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    ))}

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addArg}
                      className="w-full"
                    >
                      <Plus className="size-4 mr-2" />
                      Ajouter un argument
                    </Button>
                  </div>

                  {typeConfig.argsPlaceholder && (
                    <p className="text-xs text-muted-foreground">
                      Exemple : {typeConfig.argsPlaceholder}
                    </p>
                  )}
                </div>

                {/* Environment Variables */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Label>Variables d'environnement</Label>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="size-3.5 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs max-w-xs">
                            Variables sensibles comme les tokens API (chiffrées côté backend)
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>

                  <div className="space-y-2">
                    {Object.entries(formData.env || {}).map(([key, value]) => (
                      <div key={key} className="flex items-center gap-2">
                        <Input
                          value={key}
                          onChange={(e) => updateEnvKey(key, e.target.value)}
                          placeholder="NOM_VARIABLE"
                          className="flex-1"
                        />
                        <Input
                          type="password"
                          value={value}
                          onChange={(e) => updateEnvValue(key, e.target.value)}
                          placeholder="valeur"
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeEnvVar(key)}
                          className="flex-shrink-0"
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    ))}

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addEnvVar}
                      className="w-full"
                    >
                      <Plus className="size-4 mr-2" />
                      Ajouter une variable
                    </Button>
                  </div>
                </div>
              </TabsContent>

              {/* JSON Import Tab */}
              <TabsContent value="json" className="mt-4">
                <JSONImportFlow onImport={handleJSONImport} />
              </TabsContent>
            </Tabs>
          )}

          {/* Footer - only show for manual or HTTP */}
          {(formData.type === 'http' || activeTab === 'manual') && (
            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
                Annuler
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? (
                  <>
                    <div className="size-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
                    {mcp ? "Enregistrement..." : "Création..."}
                  </>
                ) : (
                  mcp ? "Enregistrer" : "Créer"
                )}
              </Button>
            </DialogFooter>
          )}
        </form>
      </DialogContent>
    </Dialog>
  )
}
