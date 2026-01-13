// Types pour l'authentification

export interface LoginDTO {
  email: string
  password: string
}

export interface RegisterDTO {
  email: string
  password: string
  name: string
}

export interface AuthResponse {
  user_id: string
  email: string
  name: string
}

export interface User {
  id: string
  email: string
  name: string
  created_at: string
  updated_at: string
  permission_level: 'full_auto' | 'validation_required' | 'no_tools'
  preferences: Record<string, any>
}
