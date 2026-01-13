"use client"

import { useEffect, useState, useCallback } from "react"
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
import MultipleSelector, { Option } from "@/components/ui/multiselect"
import { AvatarUpload } from "@/components/ui/avatar-upload"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { FileText, Plus, Trash2, User, Settings, Server as ServerIcon, HardDrive, Youtube, Info } from "lucide-react"
import { toast } from "sonner"
import type { AgentCapability } from "@/lib/api"
import type { AgentMCPConfig, AgentResource, AgentResourceHydrated, AgentMCPConfigHydrated } from "@/services/agents/agents.types"
import { MCPTree } from "@/components/mcp/mcp-tree"
import { ResourceCombobox } from "@/components/ui/resource-selector"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip"
import { useMCPServers } from "@/services/mcp/mcp.hooks"
import { useResources } from "@/services/resources/resources.hooks"

interface Agent {
  id?: string
  name: string
  description?: string
  avatar?: string | File
  tags?: string[]
  system_prompt: string
  documents?: File[]
  youtube_url?: string
  capabilities?: AgentCapability[]
  mcp_configs?: AgentMCPConfig[]
  resources?: AgentResource[]
}

interface AgentModalProps {
  open: boolean
  onClose: () => void
  agent?: Agent
  onSave?: (agent: Agent) => void
  saving?: boolean
}

export function AgentModal({ open, onClose, agent, onSave, saving = false }: AgentModalProps) {
  const [formData, setFormData] = useState<Agent>({
    name: "",
    description: "",
    avatar: "",
    tags: [],
    system_prompt: "",
    documents: [],
    capabilities: [],
    mcp_configs: [],
    resources: [],
  })

  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [youtubeUrl, setYoutubeUrl] = useState("")
  const [isSelectingFile, setIsSelectingFile] = useState(false)

  // MCP states (hydratés pour l'UI)
  const [mcpConfigs, setMcpConfigs] = useState<AgentMCPConfigHydrated[]>([])

  // Resource states (hydratés pour l'UI)
  const [resources, setResources] = useState<AgentResourceHydrated[]>([])
  const [pendingResources, setPendingResources] = useState<Array<{ id: string; resourceId: string }>>([])
  const [nextPendingId, setNextPendingId] = useState(1)

  // React Query hooks
  const { data: availableMCPServers = [] } = useMCPServers({ with_tools: true }) as { data: import('@/services/mcp/mcp.types').MCPServerWithTools[] }
  const { data: availableResourcesData = [] } = useResources()

  // Fonctions d'hydratation: combinent les relations avec les entités complètes
  const hydrateResources = useCallback((
    agentResources: AgentResource[],
  ): AgentResourceHydrated[] => {
    return agentResources
      .map(ar => {
        const fullResource = availableResourcesData.find(r => r.id === ar.id)
        if (!fullResource) return null
        return {
          ...fullResource,
          enabled: ar.enabled
        }
      })
      .filter(Boolean) as AgentResourceHydrated[]
  }, [availableResourcesData])

  const hydrateMCPConfigs = useCallback((
    agentMCPConfigs: AgentMCPConfig[],
  ): AgentMCPConfigHydrated[] => {
    console.log('🔧 [HYDRATE] Input:', {
      agentMCPConfigs,
      firstConfig: agentMCPConfigs[0],
      firstConfigTools: agentMCPConfigs[0]?.tools
    })

    const result = agentMCPConfigs
      .map(config => {
        const server = availableMCPServers.find(s => s.id === config.server_id)
        console.log('🔧 [HYDRATE] Processing config:', {
          configServerId: config.server_id,
          serverFound: !!server,
          configTools: config.tools,
          serverTools: server?.tools.map(t => ({ id: t.id, name: t.name }))
        })

        if (!server) return null

        // Hydrater les tools: enrichir avec les données complètes du serveur
        const hydratedTools = config.tools.map(t => {
          const fullTool = server.tools.find(st => st.id === t.id)
          console.log('🔧 [HYDRATE] Tool:', {
            toolId: t.id,
            toolEnabled: t.enabled,
            fullToolFound: !!fullTool,
            fullToolName: fullTool?.name
          })
          return {
            id: t.id,
            name: fullTool?.name || t.name || 'Unknown',
            description: fullTool?.description || t.description || null,
            enabled: t.enabled
          }
        })

        const hydrated = {
          id: config.id,
          server_id: config.server_id,
          server_name: server.name,
          server_description: server.description,
          enabled: config.enabled,
          tools: hydratedTools
        }

        console.log('🔧 [HYDRATE] Result:', hydrated)
        return hydrated
      })
      .filter(Boolean) as AgentMCPConfigHydrated[]

    console.log('🔧 [HYDRATE] Final result:', result)
    return result
  }, [availableMCPServers])

  // Sync formData with agent prop
  useEffect(() => {
    if (open) {
      if (agent) {
        console.log('🎬 [USEEFFECT] Agent received:', {
          agent,
          mcp_configs: agent.mcp_configs,
          firstConfig: agent.mcp_configs?.[0],
          firstConfigTools: agent.mcp_configs?.[0]?.tools
        })

        // Hydrater les données pour l'UI
        const hydratedResources = hydrateResources(agent.resources || [])
        const hydratedMCPConfigs = hydrateMCPConfigs(agent.mcp_configs || [])

        console.log('🎬 [USEEFFECT] After hydration:', {
          hydratedMCPConfigs
        })

        setFormData({
          id: agent.id,
          name: agent.name || "",
          description: agent.description || "",
          avatar: agent.avatar || "",
          tags: agent.tags || [],
          system_prompt: agent.system_prompt || "",
          documents: agent.documents || [],
          capabilities: agent.capabilities || [],
          mcp_configs: agent.mcp_configs || [],
          resources: agent.resources || [],
        })
        setMcpConfigs(hydratedMCPConfigs)
        setResources(hydratedResources)
      } else {
        setFormData({
          name: "",
          description: "",
          avatar: "",
          tags: [],
          system_prompt: "",
          documents: [],
          capabilities: [],
          mcp_configs: [],
          resources: [],
        })
        setMcpConfigs([])
        setResources([])
      }
    }
  }, [open, agent, hydrateResources, hydrateMCPConfigs, availableMCPServers])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Convertir les données hydratées en relations simples pour l'API
    const apiMCPConfigs: AgentMCPConfig[] = mcpConfigs.map(config => ({
      id: config.id,
      server_id: config.server_id,
      enabled: config.enabled,
      tools: config.tools.map(t => ({
        id: t.id,
        name: t.name,
        description: t.description,
        enabled: t.enabled
      }))
    }))

    const apiResources: AgentResource[] = resources.map(r => ({
      id: r.id,
      enabled: r.enabled
    }))

    const finalData: Agent = {
      ...formData,
      avatar: avatarFile || formData.avatar,
      youtube_url: youtubeUrl || undefined,
      mcp_configs: apiMCPConfigs,
      resources: apiResources,
    }

    onSave?.(finalData)
  }

  // MCP handlers
  const handleToggleMCPServer = (serverId: string, enabled: boolean) => {
    const existingConfig = mcpConfigs.find(c => c.server_id === serverId)

    if (existingConfig) {
      setMcpConfigs(mcpConfigs.map(c =>
        c.server_id === serverId
          ? {
              ...c,
              enabled,
              // Si on désactive le serveur, désactiver tous les outils
              tools: enabled ? c.tools : c.tools.map(t => ({ ...t, enabled: false }))
            }
          : c
      ))
    } else {
      const server = availableMCPServers.find(s => s.id === serverId)
      if (server) {
        setMcpConfigs([...mcpConfigs, {
          id: String(Date.now()),
          server_id: serverId,
          server_name: server.name,
          server_description: server.description,
          enabled,
          tools: server.tools.map(t => ({
            id: t.id,
            name: t.name,
            description: t.description,
            enabled: enabled
          }))
        }])
      }
    }
  }

  const handleToggleMCPTool = (serverId: string, toolId: string, enabled: boolean) => {
    setMcpConfigs(mcpConfigs.map(config => {
      if (config.server_id === serverId) {
        return {
          ...config,
          tools: config.tools.map(t =>
            t.id === toolId ? { ...t, enabled } : t
          )
        }
      }
      return config
    }))
  }

  // Resource handlers
  const handleAddPendingResource = () => {
    const newPending = {
      id: `pending-${nextPendingId}`,
      resourceId: ""
    }
    setPendingResources([...pendingResources, newPending])
    setNextPendingId(nextPendingId + 1)
  }

  const handleSelectResource = (pendingId: string, resourceId: string) => {
    // Ajouter la ressource sélectionnée aux ressources de l'agent (déjà hydratée)
    const selectedResource = availableResourcesData.find(r => r.id === resourceId)
    if (selectedResource && !resources.find(r => r.id === resourceId)) {
      const hydratedResource: AgentResourceHydrated = {
        ...selectedResource,
        enabled: true
      }
      setResources(prev => [...prev, hydratedResource])
    }

    // Supprimer la ligne pending une fois la sélection faite
    setPendingResources(prev => prev.filter(p => p.id !== pendingId))
  }

  const handleRemovePendingResource = (pendingId: string) => {
    setPendingResources(pendingResources.filter(p => p.id !== pendingId))
  }

  const handleToggleResource = (id: string, enabled: boolean) => {
    setResources(resources.map(r =>
      r.id === id ? { ...r, enabled } : r
    ))
  }

  const handleDeleteResource = (id: string) => {
    setResources(resources.filter(r => r.id !== id))
  }

  const hasUnfilledPendingResource = pendingResources.some(p => !p.resourceId)

  const isSubmitDisabled = saving || hasUnfilledPendingResource

  // Compute checked items for MCP tree (depuis les configs hydratées)
  const checkedServers = mcpConfigs.filter(c => c.enabled).map(c => c.server_id)
  const checkedTools = mcpConfigs.flatMap(c =>
    c.tools.filter(t => t.enabled).map(t => t.id)
  )

  console.log('✅ [CHECKED] Computing checked items:', {
    mcpConfigs,
    checkedServers,
    checkedTools,
    firstConfigTools: mcpConfigs[0]?.tools
  })

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent
        className="max-w-2xl max-h-[90vh] overflow-y-auto"
        onInteractOutside={(e) => {
          // Empêcher la fermeture pendant la sélection de fichier
          if (isSelectingFile) {
            e.preventDefault()
          }
        }}
      >
        <DialogHeader>
          <DialogTitle>{agent ? "Edit Agent" : "Create Agent"}</DialogTitle>
          <DialogDescription>
            {agent
              ? "Modify the agent's information below"
              : "Fill in the details to create a new agent"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Accordion type="multiple" defaultValue={["basic", "config"]} className="w-full space-y-2">
            {/* Section Informations de Base */}
            <AccordionItem value="basic" className="border rounded-lg px-4">
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-3">
                  <User className="size-4 text-muted-foreground" />
                  <div className="text-left">
                    <div className="font-semibold">Informations de base</div>
                    <div className="text-xs text-muted-foreground font-normal">
                      Avatar, nom, description et tags de l'agent
                    </div>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4">
                <div className="flex justify-center">
                  <AvatarUpload
                    defaultUrl={typeof formData.avatar === "string" ? formData.avatar : undefined}
                    onFileChange={(file) => {
                      setIsSelectingFile(false)
                      setAvatarFile(file)
                    }}
                    onFilePickerOpen={() => setIsSelectingFile(true)}
                  />
                </div>

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
                    placeholder="Nom de l'agent"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    placeholder="Brève description de l'agent"
                    rows={3}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tags">Tags</Label>
                  <MultipleSelector
                    value={(formData.tags || []).map(tag => ({ value: tag, label: tag }))}
                    onChange={(options) => setFormData({ ...formData, tags: options.map(o => o.value) })}
                    placeholder="Sélectionner ou créer des tags"
                    creatable
                    hideClearAllButton
                  />
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Section Configuration */}
            <AccordionItem value="config" className="border rounded-lg px-4">
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-3">
                  <Settings className="size-4 text-muted-foreground" />
                  <div className="text-left">
                    <div className="font-semibold">Configuration</div>
                    <div className="text-xs text-muted-foreground font-normal">
                      Prompt système et comportement de l'agent
                    </div>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label htmlFor="system_prompt">
                    System Prompt <span className="text-destructive">*</span>
                  </Label>
                  <Textarea
                    id="system_prompt"
                    required
                    value={formData.system_prompt}
                    onChange={(e) =>
                      setFormData({ ...formData, system_prompt: e.target.value })
                    }
                    placeholder="Entrez le prompt système pour cet agent"
                    rows={8}
                  />
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Section MCP Servers */}
            <AccordionItem value="mcp" className="border rounded-lg px-4">
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-3">
                  <ServerIcon className="size-4 text-muted-foreground" />
                  <div className="text-left">
                    <div className="font-semibold">MCP Servers & Outils</div>
                    <div className="text-xs text-muted-foreground font-normal">
                      Gérez les serveurs MCP et leurs outils disponibles
                    </div>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="pt-4">
                {availableMCPServers.length > 0 ? (
                  <div className="border rounded-lg p-3 max-h-[300px] overflow-y-auto">
                    <MCPTree
                      servers={availableMCPServers}
                      onToggleServer={handleToggleMCPServer}
                      onToggleTool={handleToggleMCPTool}
                      checkedServers={checkedServers}
                      checkedTools={checkedTools}
                    />
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4 border rounded-lg">
                    Aucun serveur MCP disponible
                  </p>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* Section Ressources */}
            <AccordionItem value="resources" className="border rounded-lg px-4">
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-3">
                  <HardDrive className="size-4 text-muted-foreground" />
                  <div className="text-left">
                    <div className="font-semibold">Ressources</div>
                    <div className="text-xs text-muted-foreground font-normal">
                      Configurez les ressources accessibles (cloud, DB, fichiers...)
                    </div>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4 pb-2">
                <div className="space-y-3">
                  {/* Header avec titre et bouton + */}
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">Ressources de l'agent</p>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      onClick={handleAddPendingResource}
                      disabled={hasUnfilledPendingResource}
                      className="size-8"
                    >
                      <Plus className="size-4" />
                    </Button>
                  </div>

                  {/* Tableau des ressources */}
                  {(resources.length > 0 || pendingResources.length > 0) && (
                    <div className="border rounded-lg overflow-hidden">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[70%]">Ressource</TableHead>
                            <TableHead className="w-[15%] text-center">Actif</TableHead>
                            <TableHead className="w-[15%]"></TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {/* Ressources existantes */}
                          {resources.map((resource) => (
                            <TableRow key={resource.id}>
                              <TableCell className="font-medium">
                                <div className="flex items-center gap-2">
                                  <FileText className="size-4" />
                                  <span>{resource.name}</span>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <button type="button" className="inline-flex">
                                        <Info className="size-3.5 text-muted-foreground hover:text-foreground transition-colors cursor-help" />
                                      </button>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                      <div className="flex items-start gap-2">
                                        <Info className="size-4 mt-0.5 flex-shrink-0" />
                                        <span>{resource.description || "Aucune description"}</span>
                                      </div>
                                    </TooltipContent>
                                  </Tooltip>
                                </div>
                              </TableCell>
                              <TableCell className="text-center">
                                <Switch
                                  checked={resource.enabled}
                                  onCheckedChange={(checked) => handleToggleResource(resource.id, checked)}
                                  className="data-[state=unchecked]:border-input data-[state=unchecked]:bg-transparent [&_span]:transition-all data-[state=unchecked]:[&_span]:size-3 data-[state=unchecked]:[&_span]:translate-x-0.5 data-[state=unchecked]:[&_span]:bg-input data-[state=unchecked]:[&_span]:shadow-none data-[state=unchecked]:[&_span]:rtl:-translate-x-0.5 scale-75"
                                />
                              </TableCell>
                              <TableCell>
                                <Button
                                  type="button"
                                  size="icon"
                                  variant="ghost"
                                  className="size-8 text-destructive hover:text-destructive"
                                  onClick={() => handleDeleteResource(resource.id)}
                                >
                                  <Trash2 className="size-4" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}

                          {/* Lignes en attente de sélection */}
                          {pendingResources.map((pending) => (
                            <TableRow key={pending.id} className="bg-muted/30">
                              <TableCell colSpan={3}>
                                <ResourceCombobox
                                  availableResources={availableResourcesData.filter(
                                    ar => !resources.find(r => r.id === ar.id)
                                  )}
                                  value={pending.resourceId}
                                  onChange={(value) => handleSelectResource(pending.id, value)}
                                  placeholder="Sélectionner une ressource..."
                                />
                              </TableCell>
                              <TableCell>
                                <Button
                                  type="button"
                                  size="icon"
                                  variant="ghost"
                                  className="size-8 text-destructive hover:text-destructive"
                                  onClick={() => handleRemovePendingResource(pending.id)}
                                >
                                  <Trash2 className="size-4" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}

                  {resources.length === 0 && pendingResources.length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-6 border rounded-lg">
                      Aucune ressource configurée. Cliquez sur + pour ajouter une ressource.
                    </p>
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Section YouTube (création uniquement) - TEMPORAIREMENT CACHÉE */}
            {false && !agent?.id && (
              <AccordionItem value="youtube" className="border rounded-lg px-4">
                <AccordionTrigger className="hover:no-underline">
                  <div className="flex items-center gap-3">
                    <Youtube className="size-4 text-muted-foreground" />
                    <div className="text-left">
                      <div className="font-semibold">Chaîne YouTube (Optionnel)</div>
                      <div className="text-xs text-muted-foreground font-normal">
                        Importez automatiquement toutes les vidéos d'une chaîne
                      </div>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="space-y-2 pt-4">
                  <p className="text-xs text-muted-foreground">
                    Ajoutez toutes les vidéos d'une chaîne YouTube lors de la création
                  </p>
                  <Input
                    id="youtube-url"
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                    placeholder="https://www.youtube.com/@channel"
                  />
                </AccordionContent>
              </AccordionItem>
            )}
          </Accordion>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitDisabled}>
              {saving ? (
                <>
                  <div className="size-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
                  {agent ? "Saving..." : "Creating..."}
                </>
              ) : (
                agent ? "Save changes" : "Create agent"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
