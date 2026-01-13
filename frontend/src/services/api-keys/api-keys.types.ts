// Types pour les clés API chiffrées

export interface ApiKey {
  id: string
  service_id: string | null
  created_at: string
  updated_at: string
}

export interface ApiKeyWithValue extends ApiKey {
  plain_value: string // Retourné uniquement à la création
}

// DTOs
export interface CreateApiKeyDTO {
  plain_value: string
  service_id: string
}

export interface UpdateApiKeyDTO {
  plain_value: string
}
