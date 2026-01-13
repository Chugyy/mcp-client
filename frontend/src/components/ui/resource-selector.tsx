"use client"

import { useId, useState } from "react"
import { CheckIcon, ChevronDownIcon, FileText } from "lucide-react"

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
import type { Resource } from "@/services/resources/resources.types"

interface ResourceComboboxProps {
  availableResources: Resource[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function ResourceCombobox({
  availableResources,
  value,
  onChange,
  placeholder = "Sélectionner une ressource"
}: ResourceComboboxProps) {
  const id = useId()
  const [open, setOpen] = useState<boolean>(false)

  const selectedResource = availableResources.find((resource) => resource.id === value)

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
            {selectedResource ? (
              <>
                <FileText className="size-4 text-muted-foreground" />
                <span>{selectedResource.name}</span>
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
            placeholder="Rechercher une ressource..."
            className="h-9"
          />
          <CommandList className="max-h-[300px]">
            <CommandEmpty className="py-6 text-center text-sm">
              Aucune ressource trouvée.
            </CommandEmpty>
            <CommandGroup>
              {availableResources.map((resource) => (
                <CommandItem
                  key={resource.id}
                  value={resource.name}
                  onSelect={() => {
                    onChange(resource.id)
                    setOpen(false)
                  }}
                  className="cursor-pointer"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <FileText className="size-4 text-muted-foreground" />
                    <div className="flex flex-col">
                      <span className="font-medium">{resource.name}</span>
                      {resource.description && (
                        <span className="text-xs text-muted-foreground line-clamp-1">
                          {resource.description}
                        </span>
                      )}
                    </div>
                  </div>
                  {value === resource.id && (
                    <CheckIcon size={16} className="ml-auto shrink-0 text-primary" />
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
