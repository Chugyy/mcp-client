import { apiClient } from '@/lib/api-client'

/**
 * Service for handling authenticated file uploads
 * All file access now requires JWT authentication via /api/v1/uploads/{upload_id}
 */
export const uploadsService = {
  /**
   * Get authenticated URL for an upload by ID
   * This returns the API endpoint that requires authentication
   */
  getUploadUrl(uploadId: string): string {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
    return `${API_URL}/uploads/${uploadId}`
  },

  /**
   * Fetch an upload file with authentication
   * Use this for downloading files or fetching blob data
   */
  async fetchUpload(uploadId: string): Promise<Blob> {
    const response = await apiClient.get(`/uploads/${uploadId}`, {
      responseType: 'blob'
    })
    return response.data
  },

  /**
   * Get a blob URL for an upload (useful for images)
   * Creates an object URL from the authenticated fetch
   */
  async getUploadBlobUrl(uploadId: string): Promise<string> {
    const blob = await this.fetchUpload(uploadId)
    return URL.createObjectURL(blob)
  }
}
