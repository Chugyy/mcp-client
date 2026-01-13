"use client"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { X } from 'lucide-react'

export interface AutomationsFiltersState {
  triggerType?: 'cron' | 'webhook' | 'date' | 'event' | 'manual'
  sortBy?: 'name-asc' | 'name-desc' | 'created-asc' | 'created-desc' | 'success-rate-desc' | 'success-rate-asc'
  dateRange?: 'today' | 'week' | 'month' | 'year'
}

interface AutomationsFiltersProps {
  filters: AutomationsFiltersState
  onFiltersChange: (filters: AutomationsFiltersState) => void
}

export function AutomationsFilters({ filters, onFiltersChange }: AutomationsFiltersProps) {
  const updateFilter = <K extends keyof AutomationsFiltersState>(
    key: K,
    value: AutomationsFiltersState[K]
  ) => {
    onFiltersChange({ ...filters, [key]: value })
  }

  const clearFilter = (key: keyof AutomationsFiltersState) => {
    const newFilters = { ...filters }
    delete newFilters[key]
    onFiltersChange(newFilters)
  }

  const clearAllFilters = () => {
    onFiltersChange({})
  }

  const activeFiltersCount = Object.keys(filters).length

  return (
    <div className="space-y-4">
      {/* Filtres */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Trigger Type */}
        <Select
          value={filters.triggerType || 'all'}
          onValueChange={(value) =>
            value === 'all' ? clearFilter('triggerType') : updateFilter('triggerType', value as any)
          }
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Déclencheur" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les triggers</SelectItem>
            <SelectItem value="cron">CRON</SelectItem>
            <SelectItem value="webhook">Webhook</SelectItem>
            <SelectItem value="date">Date</SelectItem>
            <SelectItem value="event">Événement</SelectItem>
            <SelectItem value="manual">Manuel</SelectItem>
          </SelectContent>
        </Select>

        {/* Sort By */}
        <Select
          value={filters.sortBy || 'created-desc'}
          onValueChange={(value) => updateFilter('sortBy', value as any)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Trier par" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="name-asc">Nom (A → Z)</SelectItem>
            <SelectItem value="name-desc">Nom (Z → A)</SelectItem>
            <SelectItem value="created-desc">Plus récent</SelectItem>
            <SelectItem value="created-asc">Plus ancien</SelectItem>
            <SelectItem value="success-rate-desc">Meilleur taux</SelectItem>
            <SelectItem value="success-rate-asc">Pire taux</SelectItem>
          </SelectContent>
        </Select>

        {/* Date Range */}
        <Select
          value={filters.dateRange || 'all'}
          onValueChange={(value) =>
            value === 'all' ? clearFilter('dateRange') : updateFilter('dateRange', value as any)
          }
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Période" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toute période</SelectItem>
            <SelectItem value="today">Aujourd'hui</SelectItem>
            <SelectItem value="week">Cette semaine</SelectItem>
            <SelectItem value="month">Ce mois</SelectItem>
            <SelectItem value="year">Cette année</SelectItem>
          </SelectContent>
        </Select>

        {/* Clear all button */}
        {activeFiltersCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearAllFilters}
            className="h-9 px-2 text-xs"
          >
            <X className="size-3 mr-1" />
            Réinitialiser ({activeFiltersCount})
          </Button>
        )}
      </div>

      {/* Active filters badges */}
      {activeFiltersCount > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">Filtres actifs :</span>
          {filters.triggerType && (
            <Badge variant="secondary" className="gap-1">
              Trigger: {filters.triggerType.toUpperCase()}
              <button
                onClick={() => clearFilter('triggerType')}
                className="ml-1 hover:bg-muted-foreground/20 rounded-full p-0.5"
              >
                <X className="size-2.5" />
              </button>
            </Badge>
          )}
          {filters.dateRange && (
            <Badge variant="secondary" className="gap-1">
              Période: {
                filters.dateRange === 'today' ? "Aujourd'hui" :
                filters.dateRange === 'week' ? 'Cette semaine' :
                filters.dateRange === 'month' ? 'Ce mois' :
                'Cette année'
              }
              <button
                onClick={() => clearFilter('dateRange')}
                className="ml-1 hover:bg-muted-foreground/20 rounded-full p-0.5"
              >
                <X className="size-2.5" />
              </button>
            </Badge>
          )}
        </div>
      )}
    </div>
  )
}
