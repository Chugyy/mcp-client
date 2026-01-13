/**
 * Types TypeScript pour le service Validations
 * Conformes aux modèles backend (app/api/models.py et app/database/models.py)
 */

// ===== INTERFACES PRINCIPALES =====

/**
 * Représentation d'une validation
 * Correspond à ValidationResponse du backend + champs supplémentaires du modèle DB
 */
export interface Validation {
  id: string
  user_id: string
  agent_id: string | null
  chat_id: string | null
  title: string
  description: string | null
  source: string
  process: string
  status: 'pending' | 'approved' | 'rejected' | 'feedback'
  tool_name: string | null
  server_id: string | null
  tool_args: Record<string, any> | null
  tool_result: Record<string, any> | null
  execution_id: string | null
  expires_at: string | null
  expired_at: string | null
  created_at: string
  updated_at: string
}

/**
 * Log d'action sur une validation (approve/reject/feedback)
 * Récupéré depuis l'endpoint GET /validations/{id}/logs
 */
export interface ValidationLog {
  id: string
  user_id: string
  agent_id: string | null
  chat_id: string | null
  type: 'validation'
  data: {
    validation_id: string
    action: 'approved' | 'rejected' | 'feedback'
    tool_name: string
    reason?: string  // Pour rejected
    feedback?: string  // Pour feedback
    always_allow?: boolean  // Pour approved
  }
  created_at: string
}

// ===== DTOs (Data Transfer Objects) =====

/**
 * DTO pour créer une nouvelle validation
 * Correspond à ValidationCreate du backend
 */
export interface ValidationCreate {
  agent_id?: string
  title: string
  description?: string
  source: string
  process: string
}

/**
 * DTO pour mettre à jour le statut d'une validation
 * Correspond à ValidationUpdate du backend
 */
export interface ValidationUpdate {
  status: 'pending' | 'validated' | 'cancelled' | 'feedback'
}

// ===== DTOs POUR ACTIONS =====

/**
 * Requête pour approuver une validation
 * Correspond à ApproveValidationRequest du backend
 */
export interface ApproveValidationRequest {
  always_allow: boolean
}

/**
 * Requête pour rejeter une validation
 * Correspond à RejectValidationRequest du backend
 */
export interface RejectValidationRequest {
  reason?: string
}

/**
 * Requête pour donner un feedback sur une validation
 * Correspond à FeedbackValidationRequest du backend
 */
export interface FeedbackValidationRequest {
  feedback: string
}

// ===== INTERFACES DE RÉPONSE =====

/**
 * Réponse lors de l'approbation d'une validation
 * Retournée par POST /validations/{id}/approve
 */
export interface ApproveValidationResponse {
  success: boolean
  message: string
  stream_active: boolean
  tool_result: any
  always_allow: boolean
}

/**
 * Réponse lors du rejet d'une validation
 * Retournée par POST /validations/{id}/reject
 */
export interface RejectValidationResponse {
  success: boolean
  message: string
  stream_active: boolean
}

/**
 * Réponse lors du feedback sur une validation
 * Retournée par POST /validations/{id}/feedback
 */
export interface FeedbackValidationResponse {
  success: boolean
  message: string
  stream_active: boolean
  feedback: string
}
