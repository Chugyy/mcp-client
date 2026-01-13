"use client"

import { ClockIcon } from "lucide-react"
import { useId } from "react"
import { DateRange } from "react-day-picker"

import { Calendar } from "@/components/ui/calendar"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

interface DateTimePickerProps {
  mode?: "single" | "range"
  selected?: Date | DateRange
  onSelect?: (date: Date | DateRange | undefined) => void
  showTime?: boolean
  defaultTime?: string
  className?: string
}

export function DateTimePicker({
  mode = "single",
  selected,
  onSelect,
  showTime = true,
  defaultTime = "12:00:00",
  className,
}: DateTimePickerProps) {
  const id = useId()

  return (
    <div className={cn("rounded-md border", className)}>
      <Calendar
        className="p-2"
        mode={mode}
        onSelect={onSelect as any}
        selected={selected as any}
      />
      {showTime && (
        <div className="border-t p-3">
          <div className="flex items-center gap-3">
            <Label className="text-xs" htmlFor={id}>
              Heure
            </Label>
            <div className="relative grow">
              <Input
                className="peer appearance-none ps-9 [&::-webkit-calendar-picker-indicator]:hidden [&::-webkit-calendar-picker-indicator]:appearance-none"
                defaultValue={defaultTime}
                id={id}
                step="1"
                type="time"
              />
              <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center justify-center ps-3 text-muted-foreground/80 peer-disabled:opacity-50">
                <ClockIcon aria-hidden="true" size={16} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
