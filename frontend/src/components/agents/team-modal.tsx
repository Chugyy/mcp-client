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
import MultipleSelector, { Option } from "@/components/ui/multiselect"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Bot, X, Info, Settings, Plus, Trash2 } from "lucide-react"
import { useChatContext } from "@/contexts/chat-context"
import { toast } from "sonner"
import type { Team, TeamAgent } from "@/lib/api"
import type { Agent } from "@/services/agents/agents.types"
import { getAvatarUrl } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { AgentCombobox } from "@/components/ui/agent-selector"

interface TeamModalProps {
  open: boolean
  onClose: () => void
  team?: Team
  onSave?: (team: Team) => void
  saving?: boolean
}

export function TeamModal({ open, onClose, team, onSave, saving = false }: TeamModalProps) {
  const { agents } = useChatContext()
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    tags: [] as string[],
    system_prompt: "",
  })

  const [selectedAgents, setSelectedAgents] = useState<TeamAgent[]>([])
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([])
  const [pendingAgents, setPendingAgents] = useState<Array<{ id: string; agentId: string }>>([])
  const [nextPendingId, setNextPendingId] = useState(1)

  useEffect(() => {
    if (open) {
      if (team) {
        setFormData({
          name: team.name || "",
          description: team.description || "",
          tags: team.tags || [],
          system_prompt: team.system_prompt || "",
        })
        setSelectedAgents(team.agents || [])
      } else {
        setFormData({
          name: "",
          description: "",
          tags: [],
          system_prompt: "",
        })
        setSelectedAgents([])
      }
      setPendingAgents([])
    }
  }, [open, team])

  useEffect(() => {
    setAvailableAgents(
      agents.filter((agent) => !selectedAgents.some((sa) => sa.agent_id === agent.id))
    )
  }, [agents, selectedAgents])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim()) {
      toast.error("Le nom de l'équipe est requis")
      return
    }

    if (!formData.system_prompt.trim()) {
      toast.error("Le prompt du chef d'équipe est requis")
      return
    }

    const teamData: Team = {
      id: team?.id || "",
      name: formData.name,
      description: formData.description,
      tags: formData.tags,
      system_prompt: formData.system_prompt,
      agents: selectedAgents,
      created_at: team?.created_at || new Date().toISOString(),
    }

    onSave?.(teamData)
  }

  const handleAddPendingAgent = () => {
    const newPending = {
      id: `pending-${nextPendingId}`,
      agentId: ""
    }
    setPendingAgents([...pendingAgents, newPending])
    setNextPendingId(nextPendingId + 1)
  }

  const handleSelectAgent = (pendingId: string, agentId: string) => {
    const selectedAgent = agents.find(a => a.id === agentId)
    if (selectedAgent && !selectedAgents.find(sa => sa.agent_id === agentId)) {
      setSelectedAgents(prev => [...prev, { agent_id: agentId, enabled: true }])
    }
    setPendingAgents(prev => prev.filter(p => p.id !== pendingId))
  }

  const handleRemovePendingAgent = (pendingId: string) => {
    setPendingAgents(pendingAgents.filter(p => p.id !== pendingId))
  }

  const handleToggleAgent = (agentId: string, enabled: boolean) => {
    setSelectedAgents(
      selectedAgents.map((sa) =>
        sa.agent_id === agentId ? { ...sa, enabled } : sa
      )
    )
  }

  const handleDeleteAgent = (agentId: string) => {
    setSelectedAgents(selectedAgents.filter((sa) => sa.agent_id !== agentId))
  }

  const getAgentById = (agentId: string) => {
    return agents.find((a) => a.id === agentId)
  }

  const hasUnfilledPendingAgent = pendingAgents.some(p => !p.agentId)
  const isSubmitDisabled = saving || hasUnfilledPendingAgent

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{team ? "Modifier l'équipe" : "Créer une équipe"}</DialogTitle>
          <DialogDescription>
            {team
              ? "Modifiez les informations de l'équipe"
              : "Remplissez les détails pour créer une nouvelle équipe"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Accordion type="multiple" defaultValue={["info", "config"]} className="w-full space-y-2">
            {/* Section Informations */}
            <AccordionItem value="info" className="border rounded-lg px-4">
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-3">
                  <Info className="size-4 text-muted-foreground" />
                  <div className="text-left">
                    <div className="font-semibold">Informations</div>
                    <div className="text-xs text-muted-foreground font-normal">
                      Nom, description et tags de l'équipe
                    </div>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label htmlFor="name">
                    Nom de l'équipe <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="name"
                    required
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    placeholder="Entrez le nom de l'équipe"
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
                    placeholder="Brève description de l'équipe"
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
                      Prompt du chef d'équipe et agents membres
                    </div>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 pt-4 pb-2">
                <div className="space-y-2">
                  <Label htmlFor="system_prompt">
                    Prompt du chef d'équipe <span className="text-destructive">*</span>
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Ce prompt gouverne toute l'équipe
                  </p>
                  <Textarea
                    id="system_prompt"
                    required
                    value={formData.system_prompt}
                    onChange={(e) =>
                      setFormData({ ...formData, system_prompt: e.target.value })
                    }
                    placeholder="Entrez le prompt pour le chef d'équipe"
                    rows={6}
                  />
                </div>

                {/* Section Agents */}
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">Agents de l'équipe</p>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      onClick={handleAddPendingAgent}
                      disabled={hasUnfilledPendingAgent}
                      className="size-8"
                    >
                      <Plus className="size-4" />
                    </Button>
                  </div>

                  {(selectedAgents.length > 0 || pendingAgents.length > 0) && (
                    <div className="border rounded-lg overflow-hidden">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[60%]">Agent</TableHead>
                            <TableHead className="w-[20%] text-center">Actif</TableHead>
                            <TableHead className="w-[20%]"></TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedAgents.map((sa) => {
                            const agent = getAgentById(sa.agent_id)
                            if (!agent) return null

                            const avatarUrl = getAvatarUrl(agent.avatar_url)

                            return (
                              <TableRow key={sa.agent_id}>
                                <TableCell className="font-medium">
                                  <div className="flex items-center gap-2">
                                    <div className="size-8 rounded-full border bg-background flex items-center justify-center overflow-hidden flex-shrink-0">
                                      {avatarUrl ? (
                                        <img src={avatarUrl} alt={agent.name} className="size-full object-cover" />
                                      ) : (
                                        <Bot className="size-4 text-muted-foreground" />
                                      )}
                                    </div>
                                    <div className="flex flex-col">
                                      <span>{agent.name}</span>
                                      {agent.description && (
                                        <span className="text-xs text-muted-foreground truncate">
                                          {agent.description}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </TableCell>
                                <TableCell className="text-center">
                                  <Switch
                                    checked={sa.enabled}
                                    onCheckedChange={(checked) => handleToggleAgent(sa.agent_id, checked)}
                                    className="data-[state=unchecked]:border-input data-[state=unchecked]:bg-transparent [&_span]:transition-all data-[state=unchecked]:[&_span]:size-3 data-[state=unchecked]:[&_span]:translate-x-0.5 data-[state=unchecked]:[&_span]:bg-input data-[state=unchecked]:[&_span]:shadow-none data-[state=unchecked]:[&_span]:rtl:-translate-x-0.5 scale-75"
                                  />
                                </TableCell>
                                <TableCell>
                                  <Button
                                    type="button"
                                    size="icon"
                                    variant="ghost"
                                    className="size-8 text-destructive hover:text-destructive"
                                    onClick={() => handleDeleteAgent(sa.agent_id)}
                                  >
                                    <Trash2 className="size-4" />
                                  </Button>
                                </TableCell>
                              </TableRow>
                            )
                          })}

                          {pendingAgents.map((pending) => (
                            <TableRow key={pending.id} className="bg-muted/30">
                              <TableCell colSpan={2}>
                                <AgentCombobox
                                  availableAgents={availableAgents}
                                  value={pending.agentId}
                                  onChange={(value) => handleSelectAgent(pending.id, value)}
                                  placeholder="Sélectionner un agent..."
                                />
                              </TableCell>
                              <TableCell>
                                <Button
                                  type="button"
                                  size="icon"
                                  variant="ghost"
                                  className="size-8 text-destructive hover:text-destructive"
                                  onClick={() => handleRemovePendingAgent(pending.id)}
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

                  {selectedAgents.length === 0 && pendingAgents.length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-6 border rounded-lg">
                      Aucun agent configuré. Cliquez sur + pour ajouter un agent.
                    </p>
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Annuler
            </Button>
            <Button type="submit" disabled={isSubmitDisabled}>
              {saving ? (
                <>
                  <div className="size-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
                  {team ? "Enregistrement..." : "Création..."}
                </>
              ) : (
                team ? "Enregistrer" : "Créer l'équipe"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
