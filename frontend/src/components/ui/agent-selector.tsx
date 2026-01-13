"use client"

import { useId, useState } from "react"
import { CheckIcon, ChevronDownIcon, Bot } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import type { Agent } from "@/lib/api"
import { getAvatarUrl } from "@/lib/api"

interface AgentComboboxProps {
  availableAgents: Agent[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function AgentCombobox({
  availableAgents,
  value,
  onChange,
  placeholder = "Sélectionner un agent"
}: AgentComboboxProps) {
  const id = useId()
  const [open, setOpen] = useState<boolean>(false)

  const selectedAgent = availableAgents.find((agent) => agent.id === value)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between border-input bg-background px-3 font-normal outline-offset-0 outline-none hover:bg-background focus-visible:outline-[3px]"
        >
          <span className={cn("flex items-center gap-2 truncate", !value && "text-muted-foreground")}>
            {selectedAgent ? (
              <>
                <div className="size-5 rounded-full border bg-background flex items-center justify-center overflow-hidden flex-shrink-0">
                  {getAvatarUrl(selectedAgent.avatar) ? (
                    <img src={getAvatarUrl(selectedAgent.avatar)} alt={selectedAgent.name} className="size-full object-cover" />
                  ) : (
                    <Bot className="size-3 text-muted-foreground" />
                  )}
                </div>
                <span>{selectedAgent.name}</span>
              </>
            ) : (
              placeholder
            )}
          </span>
          <ChevronDownIcon
            size={16}
            className="shrink-0 text-muted-foreground/80 ml-2"
            aria-hidden="true"
          />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-full min-w-[var(--radix-popper-anchor-width)] border bg-background p-0 shadow-lg"
        align="start"
        sideOffset={4}
      >
        <Command className="bg-background rounded-lg">
          <CommandInput
            placeholder="Rechercher un agent..."
            className="h-9"
          />
          <CommandList className="max-h-[300px]">
            <CommandEmpty className="py-6 text-center text-sm">
              Aucun agent trouvé.
            </CommandEmpty>
            <CommandGroup>
              {availableAgents.map((agent) => {
                const avatarUrl = getAvatarUrl(agent.avatar)
                return (
                  <CommandItem
                    key={agent.id}
                    value={agent.name}
                    onSelect={() => {
                      onChange(agent.id)
                      setOpen(false)
                    }}
                    className="cursor-pointer"
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <div className="size-8 rounded-full border bg-background flex items-center justify-center overflow-hidden flex-shrink-0">
                        {avatarUrl ? (
                          <img src={avatarUrl} alt={agent.name} className="size-full object-cover" />
                        ) : (
                          <Bot className="size-4 text-muted-foreground" />
                        )}
                      </div>
                      <div className="flex flex-col">
                        <span className="font-medium">{agent.name}</span>
                        {agent.description && (
                          <span className="text-xs text-muted-foreground truncate">
                            {agent.description}
                          </span>
                        )}
                      </div>
                    </div>
                    {value === agent.id && (
                      <CheckIcon size={16} className="ml-auto shrink-0 text-primary" />
                    )}
                  </CommandItem>
                )
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
