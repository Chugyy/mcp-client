/**
 * Utilitaires pour les ressources RAG
 */

type ResourceStatus = 'pending' | 'processing' | 'ready' | 'error'

interface StatusBadgeConfig {
  label: string
  variant: 'default' | 'outline' | 'destructive' | 'secondary'
  className?: string
}

/**
 * Retourne la configuration du badge selon le statut de la ressource
 */
export function getStatusBadge(status: ResourceStatus): StatusBadgeConfig {
  const config: Record<ResourceStatus, StatusBadgeConfig> = {
    pending: {
      label: 'En attente',
      variant: 'outline',
      className: 'border-muted-foreground/30 text-muted-foreground',
    },
    processing: {
      label: 'Traitement...',
      variant: 'default',
      className: 'bg-blue-500 text-white border-blue-500',
    },
    ready: {
      label: 'Prêt',
      variant: 'default',
      className: 'bg-green-500 text-white border-green-500',
    },
    error: {
      label: 'Erreur',
      variant: 'destructive',
    },
  }

  return config[status]
}

/**
 * Formate une date pour l'affichage
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) return '-'

  const date = new Date(dateString)
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/**
 * Formate une date avec l'heure
 */
export function formatDateTime(dateString: string | null): string {
  if (!dateString) return '-'

  const date = new Date(dateString)
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
