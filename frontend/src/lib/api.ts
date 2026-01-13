import * as mock from "./mock";

export interface AgentCapability {
  id: string;
  title: string;
  description: string;
  enabled: boolean;
}

export interface Agent {
  id: string;
  name: string;
  system_prompt: string;
  description?: string;
  avatar?: string;
  tags?: string[];
  created_at: string;
  documents_count?: number;
  enabled?: boolean;
  capabilities?: AgentCapability[];
  mcp_configs?: AgentMCPConfig[];
  resources?: AgentResource[];
}

export interface TeamAgent {
  agent_id: string;
  enabled: boolean;
}

export interface Team {
  id: string;
  name: string;
  description?: string;
  tags?: string[];
  system_prompt: string;
  agents: TeamAgent[];
  created_at: string;
  enabled?: boolean;
}

export interface Chat {
  id: string;
  user_id: number;
  agent_id: string;
  title: string;
  created_at: string;
}

export interface Message {
  id: string;
  chat_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface Document {
  id: string;
  filename: string;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
}

export interface MCPServer {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  tools: MCPTool[];
}

export interface MCPTool {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  server_id: string;
}

// Types pour les ressources RAG conformes au backend
export interface Resource {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  status: 'pending' | 'processing' | 'ready' | 'error';
  chunk_count: number;
  embedding_model: string;
  embedding_dim: number;
  indexed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// Upload = fichier physique dans une resource
export interface Upload {
  id: string;
  resource_id: string | null;
  filename: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  type: 'avatar' | 'document' | 'resource';
  created_at: string;
}

// Resource avec ses uploads (pour l'affichage UI)
export interface ResourceWithUploads extends Resource {
  uploads: Upload[];
}

export interface CreateResourceDTO {
  name: string;
  description?: string | null;
  enabled?: boolean;
}

export interface UpdateResourceDTO {
  name?: string;
  description?: string | null;
  enabled?: boolean;
}

export interface AgentResource {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  config?: Record<string, any>;
}

// AgentMCPConfig moved to @/services/agents/agents.types.ts

export interface ValidationItem {
  id: string;
  title: string;
  description: string;
  source: string;
  process: string;
  agent?: string;
  user: string;
  created_at: string;
  status: 'pending' | 'validated' | 'cancelled' | 'feedback';
}

/**
 * Get authenticated upload URL for avatars
 *
 * MIGRATION NOTE (Story 0.7):
 * - BEFORE: Avatars were public files at /uploads/avatar/{filename}
 * - AFTER: Avatars require authentication via /api/v1/uploads/{upload_id}
 *
 * The backend now returns upload_id instead of file paths.
 * This function constructs the authenticated endpoint URL.
 *
 * @param uploadId - The upload ID (not a file path anymore)
 * @returns Authenticated API endpoint URL or undefined
 */
export function getAvatarUrl(uploadId?: string): string | undefined {
  if (!uploadId) return undefined

  // Si c'est déjà une URL complète, la retourner telle quelle (rétrocompatibilité)
  if (uploadId.startsWith('http://') || uploadId.startsWith('https://')) {
    return uploadId
  }

  // Construire l'URL du nouvel endpoint authentifié
  // Format: /api/v1/uploads/{upload_id}
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
  return `${API_URL}/uploads/${uploadId}`
}

// DEPRECATED: Les fonctions ci-dessous utilisent des mocks et sont en cours de migration
// Utilisez les hooks React Query dans /services/ à la place

// Agents - Utilisez services/agents/agents.hooks.ts
export const getAgents = mock.mockGetAgents;
export const createAgent = mock.mockCreateAgent;
export const updateAgent = mock.mockUpdateAgent;
export const deleteAgent = mock.mockDeleteAgent;
export const duplicateAgent = mock.mockDuplicateAgent;
export const toggleAgent = mock.mockToggleAgent;

// Users - Utilisez services/users/users.hooks.ts
export const getUser = mock.mockGetUser;

// MCP Servers - DEPRECATED - Utilisez services/mcp/mcp.hooks.ts
// Ces exports sont conservés temporairement pour compatibilité
// mais ne sont plus utilisés dans /settings

// ============================================================================
// VALIDATIONS - DEPRECATED
// ============================================================================
// ⚠️ Ces fonctions sont DÉPRÉCIÉES et utilisent des mocks temporaires.
// ⚠️ NE PLUS UTILISER - Migration terminée vers services/validations/
//
// Pour le système de validations de tool calls, utilisez :
// - services/validations/validations.hooks.ts (hooks React Query)
// - services/validations/validations.service.ts (fonctions API)
// - services/validations/validations.types.ts (types TypeScript)
//
// Ces exports sont conservés temporairement pour rétro-compatibilité mais
// seront supprimés dans une version future.
// ============================================================================
export const getValidationItems = mock.mockGetValidationItems;
export const getArchivedItems = mock.mockGetArchivedItems;
export const validateItem = mock.mockValidateItem;
export const cancelItem = mock.mockCancelItem;
export const requestFeedback = mock.mockRequestFeedback;

// Teams - À migrer vers services/teams/
export const getTeams = mock.mockGetTeams;
export const createTeam = mock.mockCreateTeam;
export const updateTeam = mock.mockUpdateTeam;
export const deleteTeam = mock.mockDeleteTeam;
export const duplicateTeam = mock.mockDuplicateTeam;
export const toggleTeam = mock.mockToggleTeam;

export async function createAgentWithFiles(
  data: {
    name: string;
    system_prompt: string;
    description?: string;
    tags?: string[];
    avatar?: File | null;
    documents?: File[];
    youtube_url?: string;
  },
  token: string
): Promise<Agent> {
  const { avatar, documents, youtube_url, ...rest } = data;
  return mock.mockCreateAgent(rest, token);
}

export async function getAgentDocuments(agentId: string, token: string): Promise<Document[]> {
  return [];
}

export async function ingestYoutubeChannel(
  agentId: string,
  channelUrl: string,
  token: string
): Promise<{ status: string; total_videos: number; ingested: number; failed: number }> {
  return { status: "mocked", total_videos: 0, ingested: 0, failed: 0 };
}
