import { apiClient } from '@/lib/api-client'
import type {
  Validation,
  ValidationLog,
  ValidationCreate,
  ValidationUpdate,
  ApproveValidationRequest,
  ApproveValidationResponse,
  RejectValidationRequest,
  RejectValidationResponse,
  FeedbackValidationRequest,
  FeedbackValidationResponse,
} from './validations.types'

// ===== QUERY KEYS =====
export const validationKeys = {
  all: ['validations'] as const,
  lists: () => [...validationKeys.all, 'list'] as const,
  filtered: (status?: string) => [...validationKeys.all, 'list', status] as const,
  detail: (id: string) => [...validationKeys.all, 'detail', id] as const,
  logs: (id: string) => [...validationKeys.all, id, 'logs'] as const,
}

// ===== SERVICE API =====
export const validationService = {
  /**
   * GET /validations - Liste toutes les validations (avec filtre optionnel par statut)
   */
  async getAll(status?: string): Promise<Validation[]> {
    const params = status ? { status_filter: status } : {}
    const { data } = await apiClient.get('/validations', { params })
    return data
  },

  /**
   * GET /validations/{id} - Récupère une validation par ID
   */
  async getById(id: string): Promise<Validation> {
    const { data } = await apiClient.get(`/validations/${id}`)
    return data
  },

  /**
   * POST /validations - Crée une nouvelle validation
   */
  async create(dto: ValidationCreate): Promise<Validation> {
    const { data } = await apiClient.post('/validations', dto)
    return data
  },

  /**
   * PATCH /validations/{id}/status - Met à jour le statut d'une validation
   */
  async updateStatus(id: string, dto: ValidationUpdate): Promise<Validation> {
    const { data } = await apiClient.patch(`/validations/${id}/status`, dto)
    return data
  },

  /**
   * POST /validations/{id}/approve - Approuve une validation et exécute le tool call
   */
  async approve(
    id: string,
    request: ApproveValidationRequest
  ): Promise<ApproveValidationResponse> {
    const { data } = await apiClient.post(`/validations/${id}/approve`, request)
    return data
  },

  /**
   * POST /validations/{id}/reject - Rejette une validation
   */
  async reject(
    id: string,
    request: RejectValidationRequest
  ): Promise<RejectValidationResponse> {
    const { data } = await apiClient.post(`/validations/${id}/reject`, request)
    return data
  },

  /**
   * POST /validations/{id}/feedback - Donne un feedback sur une validation
   */
  async feedback(
    id: string,
    request: FeedbackValidationRequest
  ): Promise<FeedbackValidationResponse> {
    const { data } = await apiClient.post(`/validations/${id}/feedback`, request)
    return data
  },

  /**
   * GET /validations/{id}/logs - Récupère les logs d'action d'une validation
   */
  async getLogs(id: string): Promise<ValidationLog[]> {
    const { data } = await apiClient.get(`/validations/${id}/logs`)
    return data
  },
}
