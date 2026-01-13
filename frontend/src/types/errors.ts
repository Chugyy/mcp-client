/**
 * Standardized error types for API responses (RFC 7807)
 *
 * Used throughout the frontend for consistent error handling
 */

/**
 * Represents a single validation error for a specific field
 */
export interface ErrorDetail {
  field: string
  message: string
  value?: any
}

/**
 * RFC 7807 Problem Details format
 *
 * Standard structure for API error responses
 */
export interface ProblemDetails {
  type: string
  title: string
  status: number
  detail: string
  instance?: string
  errors?: ErrorDetail[]
  timestamp?: string
  [key: string]: any  // Index signature for custom extensions (e.g., impact)
}

/**
 * API Error Response - Union type for backward compatibility
 *
 * Supports both RFC 7807 format and legacy formats
 */
export interface ApiErrorResponse {
  // RFC 7807 fields (all optional for flexibility)
  type?: string
  title?: string
  status?: number
  detail?: string | object[]  // Support both RFC 7807 string and Pydantic raw array
  instance?: string
  errors?: ErrorDetail[]
  timestamp?: string

  // Legacy format fields
  message?: string

  // Extensions (e.g., impact for ConflictError)
  [key: string]: any
}
