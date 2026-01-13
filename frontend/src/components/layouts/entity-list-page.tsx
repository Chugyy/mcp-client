"use client"

import { ReactNode } from 'react'
import { Search, LucideIcon } from 'lucide-react'
import { AppLayout } from '@/components/layouts/app-layout'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { AlertCircle } from 'lucide-react'

interface CreateButtonConfig {
  label: string
  icon?: LucideIcon
  onClick: () => void
  disabled?: boolean
}

interface EmptyStateConfig {
  icon: LucideIcon
  title: string
  description: string
}

interface EntityListPageProps<T> {
  // Header
  title: string
  description?: string

  // Search
  searchPlaceholder?: string
  searchValue?: string
  onSearchChange?: (value: string) => void
  showSearch?: boolean

  // Create button
  createButton?: CreateButtonConfig

  // Custom filters (slot)
  filters?: ReactNode

  // Data
  items: T[]
  isLoading?: boolean
  error?: Error | null

  // Rendering
  renderItem: (item: T) => ReactNode
  getItemKey: (item: T) => string

  // Empty states
  emptyState?: EmptyStateConfig
  searchEmptyState?: EmptyStateConfig

  // Grid configuration
  gridCols?: string

  // Custom content (after header, before grid)
  headerActions?: ReactNode

  // Loading skeleton count
  loadingSkeletonCount?: number
}

export function EntityListPage<T>({
  title,
  description,
  searchPlaceholder = "Rechercher...",
  searchValue = "",
  onSearchChange,
  showSearch = true,
  createButton,
  filters,
  items,
  isLoading = false,
  error = null,
  renderItem,
  getItemKey,
  emptyState,
  searchEmptyState,
  gridCols = "md:grid-cols-2 lg:grid-cols-3",
  headerActions,
  loadingSkeletonCount = 6,
}: EntityListPageProps<T>) {
  const hasSearchQuery = searchValue.trim().length > 0

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
          {description && (
            <p className="text-muted-foreground mt-1">{description}</p>
          )}
        </div>

        {/* Search bar + Create button */}
        {(showSearch || createButton) && (
          <div className="mb-6 flex items-center justify-between gap-4">
            {showSearch && (
              <div className="relative max-w-md flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  placeholder={searchPlaceholder}
                  value={searchValue}
                  onChange={(e) => onSearchChange?.(e.target.value)}
                  className="pl-10"
                />
              </div>
            )}

            {createButton && (
              <Button
                onClick={createButton.onClick}
                disabled={createButton.disabled}
                size="icon"
                variant="ghost"
                className="h-10 w-10"
              >
                {createButton.icon && <createButton.icon className="size-5" />}
              </Button>
            )}
          </div>
        )}

        {/* Custom filters */}
        {filters && <div className="mb-6">{filters}</div>}

        {/* Header actions (custom content) */}
        {headerActions && <div className="mb-6">{headerActions}</div>}

        {/* Content */}
        <div>
          {/* Loading state */}
          {isLoading && (
            <div className={`grid grid-cols-1 ${gridCols} gap-4`}>
              {Array.from({ length: loadingSkeletonCount }).map((_, i) => (
                <Skeleton key={i} className="h-48 w-full" />
              ))}
            </div>
          )}

          {/* Error state */}
          {!isLoading && error && (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <AlertCircle className="size-12 text-destructive" />
              <div className="text-center">
                <h3 className="text-lg font-semibold">Erreur de chargement</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {error.message || "Une erreur est survenue. Veuillez réessayer."}
                </p>
              </div>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && items.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              {hasSearchQuery && searchEmptyState ? (
                <>
                  <searchEmptyState.icon className="size-16 opacity-50" />
                  <div className="text-center">
                    <h3 className="text-lg font-semibold">
                      {searchEmptyState.title}
                    </h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      {searchEmptyState.description}
                    </p>
                  </div>
                </>
              ) : emptyState ? (
                <>
                  <emptyState.icon className="size-16 opacity-50" />
                  <div className="text-center">
                    <h3 className="text-lg font-semibold">{emptyState.title}</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      {emptyState.description}
                    </p>
                  </div>
                </>
              ) : (
                <div className="text-center">
                  <p className="text-muted-foreground">Aucun élément trouvé</p>
                </div>
              )}
            </div>
          )}

          {/* Grid of items */}
          {!isLoading && !error && items.length > 0 && (
            <div className={`grid grid-cols-1 ${gridCols} gap-4`}>
              {items.map((item) => (
                <div key={getItemKey(item)}>{renderItem(item)}</div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
