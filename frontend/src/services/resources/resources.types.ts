// Types pour les resources conformes à l'API Backend

export type ResourceType = 'cloud' | 'database' | 'files' | 'api'

export interface Upload {
  id: string
  user_id: string | null
  agent_id: string | null
  resource_id: string | null
  type: string
  filename: string
  file_path: string
  file_size: number | null
  mime_type: string | null
  created_at: string
}

export interface Resource {
  id: string
  name: string
  description: string | null
  type: ResourceType
  enabled: boolean
  status: string
  chunk_count: number
  embedding_model: string
  embedding_dim: number
  indexed_at: string | null
  error_message: string | null
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface ResourceWithUploads extends Resource {
  uploads: Upload[]
}

// DTOs
export interface CreateResourceDTO {
  name: string
  description?: string | null
  enabled?: boolean
  embedding_model?: string
  embedding_dim?: number
}

export interface UpdateResourceDTO {
  name?: string | null
  description?: string | null
  enabled?: boolean | null
}
