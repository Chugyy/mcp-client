// Types pour les services LLM (OpenAI, Anthropic, etc.)

export interface Service {
  id: string
  name: string // "OpenAI", "Anthropic"
  provider: string // "openai", "anthropic"
  description: string | null
  status: 'active' | 'inactive' | 'deprecated'
  created_at: string
  updated_at: string
}

export interface UserProvider {
  id: string
  user_id: string
  service_id: string
  api_key_id: string | null
  enabled: boolean
  created_at: string
  updated_at: string
}

// DTOs
export interface CreateUserProviderDTO {
  service_id: string
  api_key_id?: string | null
  enabled?: boolean
}

export interface UpdateUserProviderDTO {
  api_key_id?: string | null
  enabled?: boolean | null
}

// Type combiné pour l'affichage UI
export interface ProviderStatus {
  service: Service
  userProvider?: UserProvider
  isConfigured: boolean
  isEnabled: boolean
}
