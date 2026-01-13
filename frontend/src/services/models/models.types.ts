export interface Model {
  id: string
  service_id: string
  model_name: string
  display_name: string | null
  description: string | null
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface ModelWithService extends Model {
  service_name: string
  provider: string
  logo_upload_id: string | null
  logo_url: string | null
}
