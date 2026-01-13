/**
 * Types TypeScript pour le service Chats
 * Conformes aux modèles backend (app/api/models.py)
 */

// ===== INTERFACES PRINCIPALES =====

/**
 * Représentation d'un chat
 * Correspond à ChatResponse du backend
 */
export interface Chat {
  id: string
  user_id: string
  agent_id: string | null
  team_id: string | null
  title: string
  model: string | null
  initialized_at: string | null
  created_at: string
  updated_at: string
}

/**
 * Représentation d'un message
 * Correspond à MessageResponse du backend
 */
export interface Message {
  id: string
  chat_id: string
  role: 'user' | 'assistant' | 'tool_call'
  content: string
  turn_id?: string
  sequence_index?: number
  metadata?: {
    sources?: Source[]
    step?: 'validation_requested' | 'executing' | 'completed' | 'failed' | 'rejected' | 'feedback_received'
    validation_id?: string
    tool_call_id?: string
    tool_name?: string
    server_id?: string
    arguments?: Record<string, any>
    status?: 'pending' | 'approved' | 'rejected'
    result?: {
      success: boolean
      result?: any
      error?: string
    }
    [key: string]: any
  }
  created_at: string
}

/**
 * Source RAG utilisée pour une réponse
 * Contient les informations de la resource et du chunk utilisé
 */
export interface Source {
  resource_id: string
  resource_name: string
  chunk_id: string
  similarity: number
  content: string
}

// ===== DTOs (Data Transfer Objects) =====

/**
 * DTO pour créer un nouveau chat
 * Correspond à ChatCreate du backend
 */
export interface ChatCreate {
  agent_id?: string
  team_id?: string
  title: string
}

/**
 * DTO pour créer un nouveau message
 * Correspond à MessageCreate du backend
 */
export interface MessageCreate {
  role: 'user' | 'assistant'
  content: string
  metadata?: Record<string, any>
}

/**
 * DTO pour streamer un message dans un chat existant
 * Correspond à MessageStreamRequest du backend
 */
export interface MessageStreamRequest {
  message: string
  model?: string
  agent_id?: string
  api_key_id?: string
}

// ===== TYPES DE STREAMING SSE =====

/**
 * Types d'événements SSE supportés pour le streaming
 * Correspond à StreamEventType du backend (app/core/utils/sse.py)
 */
export enum StreamEventType {
  CHUNK = 'chunk',
  SOURCES = 'sources',
  VALIDATION_REQUIRED = 'validation_required',
  STOPPED = 'stopped',
  ERROR = 'error',
  DONE = 'done',
  // Nouveaux events pour architecture de segmentation
  USER_MESSAGE_CREATED = 'user_message_created',
  TEXT_SEGMENT_DONE = 'text_segment_done',
  TOOL_EXECUTING = 'tool_executing',
  TOOL_COMPLETED = 'tool_completed',
  ASSISTANT_MESSAGE_SAVED = 'assistant_message_saved',
}

/**
 * Callbacks pour gérer les événements du stream SSE
 */
export interface StreamCallbacks {
  onChunk: (content: string) => void
  onSources: (sources: Source[]) => void
  onValidationRequired: (validationId: string) => void
  onRefetchMessages: () => void  // Nouvelle callback pour refetch messages
  onError: (error: string) => void
  onDone: () => void
}

/**
 * Événement de type CHUNK
 * Contient un morceau de texte de la réponse LLM
 */
export interface StreamChunkEvent {
  content: string
}

/**
 * Événement de type SOURCES
 * Contient les sources RAG utilisées pour la réponse
 */
export interface StreamSourcesEvent {
  sources: Source[]
}

/**
 * Événement de type VALIDATION_REQUIRED
 * Indique qu'une validation humaine est requise pour un tool call
 */
export interface StreamValidationRequiredEvent {
  validation_id: string
}

/**
 * Événement de type ERROR
 * Contient un message d'erreur
 */
export interface StreamErrorEvent {
  message: string
}

/**
 * Événement de type USER_MESSAGE_CREATED
 * Confirme que le message utilisateur a été créé en DB
 */
export interface StreamUserMessageCreatedEvent {
  message_id: string
  content: string
  created_at: string
}

/**
 * Événement de type TEXT_SEGMENT_DONE
 * Indique qu'un segment de texte est terminé et sauvegardé
 */
export interface StreamTextSegmentDoneEvent {
  content: string
  segment_index: number
  message_id: string
  stopped?: boolean
  final?: boolean
}

/**
 * Événement de type TOOL_EXECUTING
 * Indique qu'un outil est en cours d'exécution
 */
export interface StreamToolExecutingEvent {
  tool_call_id: string
  tool_name?: string
  validation_id?: string
}

/**
 * Événement de type TOOL_COMPLETED
 * Indique qu'un outil a terminé son exécution
 */
export interface StreamToolCompletedEvent {
  tool_call_id: string
  success: boolean
  result_preview?: string
}

/**
 * Événement de type ASSISTANT_MESSAGE_SAVED
 * Confirme que le message assistant complet est sauvegardé
 */
export interface StreamAssistantMessageSavedEvent {
  message_id: string
  segment_count: number
  total_length?: number
}
