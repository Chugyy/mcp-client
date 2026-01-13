/**
 * Error handling utilities for API responses
 *
 * Supports multiple error formats:
 * - RFC 7807 ProblemDetails (new backend format)
 * - Legacy Pydantic validation errors
 * - Network errors
 * - Generic HTTP errors
 */

import { ApiErrorResponse, ErrorDetail, ProblemDetails } from '@/types/errors'

/**
 * Extracts a user-friendly error message from an Axios error
 *
 * Priority order:
 * 1. Network errors (no response)
 * 2. RFC 7807 simple detail string
 * 3. RFC 7807 validation errors array
 * 4. Legacy Pydantic raw format
 * 5. Custom message field
 * 6. HTTP status code fallback
 *
 * @param error - Axios error object
 * @returns User-friendly error message
 */
export function extractErrorMessage(error: any): string {
  // 1. Network errors (no response)
  if (!error.response) {
    if (error.message === 'Network Error') {
      return 'Impossible de contacter le serveur. Vérifiez votre connexion.'
    }
    if (error.code === 'ECONNABORTED') {
      return 'La requête a expiré. Veuillez réessayer.'
    }
    return error.message || 'Une erreur réseau est survenue'
  }

  const data: ApiErrorResponse = error.response?.data
  const status = error.response?.status

  // 2. RFC 7807 validation errors (priority 1 - most specific)
  if (Array.isArray(data?.errors) && data.errors.length > 0) {
    const firstError = data.errors[0]
    return `${firstError.field}: ${firstError.message}`
  }

  // 3. RFC 7807 format with simple detail string (priority 2)
  if (typeof data?.detail === 'string' && data.detail) {
    return data.detail
  }

  // 4. Legacy Pydantic raw format (priority 3 - backward compatibility)
  if (Array.isArray(data?.detail) && data.detail.length > 0) {
    const firstError = data.detail[0]
    const loc = firstError.loc || []
    // Ignore first element ('body', 'query', 'path') and join rest
    const field = loc.slice(1).join(' → ') || 'Champ'
    const message = firstError.msg || 'Erreur de validation'
    return `${field}: ${message}`
  }

  // 5. Custom message field (priority 4)
  if (typeof data?.message === 'string') {
    return data.message
  }

  // 6. HTTP status code fallback (priority 5)
  switch (status) {
    case 400:
      return 'Requête invalide'
    case 401:
      return 'Authentification requise'
    case 403:
      return 'Accès refusé'
    case 404:
      return 'Ressource non trouvée'
    case 409:
      return 'Conflit détecté'
    case 422:
      return 'Données invalides'
    case 429:
      return 'Trop de requêtes. Veuillez patienter.'
    case 500:
      return 'Erreur serveur. Veuillez réessayer.'
    case 503:
      return 'Service temporairement indisponible'
    default:
      return 'Une erreur est survenue'
  }
}

/**
 * Extracts all validation errors from an API error response
 *
 * Useful for displaying multiple field errors (Phase 2)
 *
 * @param error - Axios error object
 * @returns Array of ErrorDetail objects
 */
export function extractValidationErrors(error: any): ErrorDetail[] {
  const data: ApiErrorResponse = error.response?.data

  // 1. RFC 7807 modern format
  if (Array.isArray(data?.errors)) {
    return data.errors
  }

  // 2. Legacy Pydantic raw format
  if (Array.isArray(data?.detail)) {
    return data.detail.map((err: any) => {
      const loc = err.loc || []
      const field = loc.slice(1).join(' → ') || 'unknown'
      return {
        field,
        message: err.msg || 'Validation error',
        value: err.input
      }
    })
  }

  // 3. No validation errors found
  return []
}

/**
 * Checks if an error is a validation error (422)
 *
 * @param error - Axios error object
 * @returns True if error status is 422
 */
export function isValidationError(error: any): boolean {
  return error.response?.status === 422
}

/**
 * Checks if an error is a network error (no response)
 *
 * @param error - Axios error object
 * @returns True if no response or explicit network error
 */
export function isNetworkError(error: any): boolean {
  return !error.response || error.message === 'Network Error'
}

/**
 * Extracts complete ProblemDetails object from an API error
 *
 * Useful for components that need access to the full error structure
 *
 * @param error - Axios error object
 * @returns ProblemDetails object or null if not available
 */
export function extractProblemDetails(error: any): ProblemDetails | null {
  // 1. No response
  if (!error.response) {
    return null
  }

  // 2. Extract data
  const data: ApiErrorResponse = error.response?.data

  // 3. If data has RFC 7807 properties, return as ProblemDetails
  if (data?.type && data?.title && data?.status && data?.detail) {
    return data as ProblemDetails
  }

  // 4. Construct ProblemDetails from legacy format
  const status = error.response?.status || 500
  const problemDetails: ProblemDetails = {
    type: 'UnknownError',
    title: 'Error',
    status,
    detail: extractErrorMessage(error),
  }

  // Add validation errors if status is 422
  if (status === 422) {
    const validationErrors = extractValidationErrors(error)
    if (validationErrors.length > 0) {
      problemDetails.errors = validationErrors
    }
  }

  return problemDetails
}
