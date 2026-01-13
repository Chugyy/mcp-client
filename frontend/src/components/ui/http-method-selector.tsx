"use client"

import { useId } from "react"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"

interface HttpMethodSelectorProps {
  value: 'GET' | 'POST' | 'PUT' | 'DELETE'
  onChange: (method: 'GET' | 'POST' | 'PUT' | 'DELETE') => void
}

export function HttpMethodSelector({ value, onChange }: HttpMethodSelectorProps) {
  const id = useId()

  const getStateFromValue = (val: string) => {
    const index = ['GET', 'POST', 'PUT', 'DELETE'].indexOf(val)
    return `state-${index}`
  }

  const getTranslateClass = (val: string) => {
    const index = ['GET', 'POST', 'PUT', 'DELETE'].indexOf(val)
    if (index === 0) return 'after:translate-x-0'
    if (index === 1) return 'after:translate-x-full'
    if (index === 2) return 'after:translate-x-[200%]'
    return 'after:translate-x-[300%]'
  }

  return (
    <div className="flex h-9 rounded-md bg-input/50 p-0.5 w-full">
      <RadioGroup
        value={value}
        onValueChange={(val) => onChange(val as 'GET' | 'POST' | 'PUT' | 'DELETE')}
        className={`group relative flex w-full grid-cols-4 items-center gap-0 text-sm font-medium after:absolute after:inset-y-0 after:w-1/4 after:rounded-sm after:bg-background after:shadow-xs after:transition-transform after:duration-300 after:ease-[cubic-bezier(0.16,1,0.3,1)] has-focus-visible:after:border-ring has-focus-visible:after:ring-[3px] has-focus-visible:after:ring-ring/50 ${getTranslateClass(value)}`}
        data-state={getStateFromValue(value)}
      >
        <label className="relative z-10 flex flex-1 h-full cursor-pointer items-center justify-center px-3 whitespace-nowrap transition-colors select-none data-[selected=false]:text-muted-foreground/70" data-selected={value === 'GET'}>
          GET
          <RadioGroupItem id={`${id}-get`} value="GET" className="sr-only" />
        </label>
        <label className="relative z-10 flex flex-1 h-full cursor-pointer items-center justify-center px-3 whitespace-nowrap transition-colors select-none data-[selected=false]:text-muted-foreground/70" data-selected={value === 'POST'}>
          POST
          <RadioGroupItem id={`${id}-post`} value="POST" className="sr-only" />
        </label>
        <label className="relative z-10 flex flex-1 h-full cursor-pointer items-center justify-center px-3 whitespace-nowrap transition-colors select-none data-[selected=false]:text-muted-foreground/70" data-selected={value === 'PUT'}>
          PUT
          <RadioGroupItem id={`${id}-put`} value="PUT" className="sr-only" />
        </label>
        <label className="relative z-10 flex flex-1 h-full cursor-pointer items-center justify-center px-3 whitespace-nowrap transition-colors select-none data-[selected=false]:text-muted-foreground/70" data-selected={value === 'DELETE'}>
          DELETE
          <RadioGroupItem id={`${id}-delete`} value="DELETE" className="sr-only" />
        </label>
      </RadioGroup>
    </div>
  )
}
