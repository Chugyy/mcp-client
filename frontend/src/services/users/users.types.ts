// Types pour l'utilisateur connecté

export interface User {
  id: string
  email: string
  name: string
  preferences: UserPreferences
  permission_level: PermissionLevel
  created_at: string
  updated_at: string
}

export interface UserPreferences {
  theme?: 'light' | 'dark' | 'system'
  language?: 'fr' | 'en'
  [key: string]: any // Permet d'ajouter d'autres préférences
}

export type PermissionLevel = 'full_auto' | 'validation_required' | 'no_tools'

// DTOs
export interface UpdateUserDTO {
  name?: string
  preferences?: UserPreferences
}

export interface UpdatePermissionLevelDTO {
  permission_level: PermissionLevel
}

// Helper type pour les labels UI
export const PERMISSION_LEVEL_LABELS: Record<PermissionLevel, { label: string; description: string }> = {
  full_auto: {
    label: 'Automatique',
    description: 'Tous les outils s\'exécutent sans validation',
  },
  validation_required: {
    label: 'Avec validation',
    description: 'Demande validation avant chaque outil (recommandé)',
  },
  no_tools: {
    label: 'Désactivé',
    description: 'Désactive complètement les outils externes',
  },
}
