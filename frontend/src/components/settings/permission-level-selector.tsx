"use client"

import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { PERMISSION_LEVEL_LABELS, type PermissionLevel } from "@/services/users/users.types"

interface PermissionLevelSelectorProps {
  value: PermissionLevel
  onValueChange: (value: PermissionLevel) => void
  disabled?: boolean
}

export function PermissionLevelSelector({
  value,
  onValueChange,
  disabled = false,
}: PermissionLevelSelectorProps) {
  return (
    <RadioGroup
      value={value}
      onValueChange={(val) => onValueChange(val as PermissionLevel)}
      disabled={disabled}
      className="space-y-3"
    >
      {Object.entries(PERMISSION_LEVEL_LABELS).map(([level, { label, description }]) => (
        <div key={level} className="flex items-start space-x-3">
          <RadioGroupItem value={level} id={level} className="mt-1" />
          <div className="flex-1">
            <Label htmlFor={level} className="font-medium cursor-pointer">
              {label}
            </Label>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
        </div>
      ))}
    </RadioGroup>
  )
}
