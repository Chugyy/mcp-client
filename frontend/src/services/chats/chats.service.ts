import { apiClient } from '@/lib/api-client'
import type {
  Chat,
  Message,
  ChatCreate,
  MessageCreate,
  MessageStreamRequest,
  StreamCallbacks,
} from './chats.types'

// ===== QUERY KEYS =====
export const chatKeys = {
  all: ['chats'] as const,
  lists: () => [...chatKeys.all, 'list'] as const,
  detail: (id: string) => [...chatKeys.all, 'detail', id] as const,
  messages: (chatId: string) => [...chatKeys.all, chatId, 'messages'] as const,
}

// ===== SERVICE API =====
export const chatService = {
  /**
   * GET /chats - Liste toutes les conversations
   */
  async getChats(): Promise<Chat[]> {
    const { data } = await apiClient.get('/chats')
    return data
  },

  /**
   * GET /chats/{id} - Récupère une conversation par ID
   */
  async getChat(id: string): Promise<Chat> {
    const { data } = await apiClient.get(`/chats/${id}`)
    return data
  },

  /**
   * POST /chats - Crée une nouvelle conversation
   */
  async createChat(dto: ChatCreate): Promise<Chat> {
    const { data } = await apiClient.post('/chats', dto)
    return data
  },

  /**
   * DELETE /chats/{id} - Supprime une conversation
   */
  async deleteChat(id: string): Promise<void> {
    await apiClient.delete(`/chats/${id}`)
  },

  /**
   * GET /chats/{id}/messages - Récupère les messages d'une conversation
   */
  async getMessages(chatId: string, limit = 100): Promise<Message[]> {
    const { data } = await apiClient.get(`/chats/${chatId}/messages`, {
      params: { limit },
    })

    // Trier en priorité par turn_id + sequence_index, puis par created_at
    return data.sort((a: Message, b: Message) => {
      // Si les deux messages appartiennent au même turn, trier par sequence_index
      if (a.turn_id && b.turn_id && a.turn_id === b.turn_id) {
        return (a.sequence_index || 0) - (b.sequence_index || 0)
      }

      // Sinon, trier par created_at (chronologie globale entre les turns)
      const timeA = new Date(a.created_at).getTime()
      const timeB = new Date(b.created_at).getTime()
      return timeA - timeB
    })
  },

  /**
   * POST /chats/{id}/messages - Envoie un message (non-streaming)
   */
  async sendMessage(chatId: string, dto: MessageCreate): Promise<Message> {
    const { data } = await apiClient.post(`/chats/${chatId}/messages`, dto)
    return data
  },

  /**
   * POST /chats/{id}/stop - Arrête un stream en cours
   */
  async stopStream(chatId: string): Promise<void> {
    await apiClient.post(`/chats/${chatId}/stop`)
  },

  /**
   * POST /chats/{id}/stream - Stream un message avec SSE
   *
   * FONCTION CRITIQUE - Parser SSE
   *
   * Format SSE standard W3C :
   * event: <type>
   * data: <json>
   * <ligne vide>
   *
   * Events supportés :
   * - chunk: Chunk de texte de la réponse LLM
   * - sources: Sources RAG utilisées
   * - validation_required: Validation humaine requise
   * - stopped: Stream arrêté par l'utilisateur
   * - error: Erreur durant le streaming
   * - done: Stream terminé avec succès
   */
  async streamMessage(
    chatId: string,
    request: MessageStreamRequest,
    callbacks: StreamCallbacks
  ): Promise<void> {
    const streamStartTime = Date.now()
    console.log(`[SSE DEBUG] 🚀 Stream START - chatId=${chatId}, timestamp=${new Date().toISOString()}`)

    let response: any
    let reader: any

    try {
      // Faire la requête POST avec responseType 'stream'
      console.log(`[SSE DEBUG] 📡 Making POST request to /chats/${chatId}/stream`)
      response = await apiClient.post(
        `/chats/${chatId}/stream`,
        request,
        {
          timeout: 0, // ✅ FIX: Désactiver le timeout pour SSE (peut durer plusieurs minutes avec validations)
          responseType: 'stream',
          headers: {
            Accept: 'text/event-stream',
          },
          // IMPORTANT: Axios avec fetch adapter pour le stream
          adapter: 'fetch',
        }
      )
      console.log(`[SSE DEBUG] ✅ POST request successful, response received`)

      // Vérifier que la réponse est un stream
      if (!response.data || typeof response.data.getReader !== 'function') {
        throw new Error('Response is not a readable stream')
      }

      // Créer un reader pour le stream
      reader = response.data
        .pipeThrough(new TextDecoderStream())
        .getReader()
      console.log(`[SSE DEBUG] 📖 Reader created successfully`)

      let buffer = ''
      let lastActivityTime = Date.now()
      let chunkCount = 0
      let isValidationPending = false

      // Timeout d'inactivité : abort si aucune donnée reçue pendant 2 minutes
      // SAUF pendant les validations humaines (pas de timeout pendant l'attente)
      const INACTIVITY_TIMEOUT = 120000 // 2 minutes

      while (true) {
        const readStartTime = Date.now()
        const timeSinceLastActivity = readStartTime - lastActivityTime

        // Vérifier le timeout d'inactivité (seulement si pas en attente de validation)
        if (!isValidationPending && timeSinceLastActivity > INACTIVITY_TIMEOUT) {
          const errorMsg = `Stream inactivity timeout: no data received for ${INACTIVITY_TIMEOUT / 1000}s (last activity: ${timeSinceLastActivity}ms ago)`
          console.error(`[SSE DEBUG] ⏱️ INACTIVITY TIMEOUT - ${errorMsg}`)
          throw new Error(errorMsg)
        }

        console.log(`[SSE DEBUG] ⏳ Waiting for next chunk... (idle time: ${timeSinceLastActivity}ms, total time: ${readStartTime - streamStartTime}ms, validation pending: ${isValidationPending})`)

        const { done, value } = await reader.read()

        const readEndTime = Date.now()
        const readDuration = readEndTime - readStartTime

        if (done) {
          console.log(`[SSE DEBUG] ✅ Stream done - Total chunks: ${chunkCount}, Duration: ${readEndTime - streamStartTime}ms`)
          break
        }

        chunkCount++
        lastActivityTime = Date.now()
        console.log(`[SSE DEBUG] 📦 Chunk #${chunkCount} received - Size: ${value.length} chars, Read took: ${readDuration}ms`)

        buffer += value

        // Split sur double newline (séparateur SSE standard)
        const events = buffer.split('\n\n')

        // Garder le dernier morceau (potentiellement incomplet)
        buffer = events.pop() || ''

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue

          // Parser SSE : event: <type>\ndata: <json>
          const lines = eventBlock.split('\n')
          const eventLine = lines.find((l) => l.startsWith('event:'))
          const dataLine = lines.find((l) => l.startsWith('data:'))

          if (!eventLine || !dataLine) {
            console.warn('[SSE] Malformed event (missing event or data line):', eventBlock)
            continue
          }

          const eventType = eventLine.replace('event:', '').trim()
          const dataStr = dataLine.replace('data:', '').trim()

          console.log(`[SSE DEBUG] 🎯 Event received: type="${eventType}"`)

          let data: any
          try {
            data = JSON.parse(dataStr)
          } catch (e) {
            console.error('[SSE] Failed to parse JSON data:', dataStr, e)
            continue
          }

          // Dispatcher selon le type d'event
          switch (eventType) {
            case 'chunk':
              // Reprise du stream après validation → réactiver le timeout d'inactivité
              if (isValidationPending) {
                console.log(`[SSE DEBUG] ✅ Stream resumed after validation`)
                isValidationPending = false
              }
              if (data.content !== undefined) {
                callbacks.onChunk(data.content)
              } else {
                console.warn('[SSE] chunk event missing content field:', data)
              }
              break

            case 'sources':
              // Sources = reprise du stream → réactiver le timeout
              if (isValidationPending) {
                console.log(`[SSE DEBUG] ✅ Stream resumed after validation (sources received)`)
                isValidationPending = false
              }
              if (Array.isArray(data.sources)) {
                callbacks.onSources(data.sources)
              } else {
                console.warn('[SSE] sources event missing sources array:', data)
              }
              break

            case 'validation_required':
              // Validation en attente → désactiver le timeout d'inactivité
              console.log(`[SSE DEBUG] 🔒 Validation required: ${data.validation_id} - Inactivity timeout DISABLED`)
              isValidationPending = true
              if (data.validation_id) {
                callbacks.onValidationRequired(data.validation_id)
              } else {
                console.warn('[SSE] validation_required event missing validation_id:', data)
              }
              break

            case 'tool_call_created':
              // Un message tool_call vient d'être créé → refetch les messages
              console.log(`[SSE DEBUG] 🔧 Tool call created - triggering refetch`)
              callbacks.onRefetchMessages()
              break

            case 'tool_call_updated':
              // Un message tool_call vient d'être mis à jour → refetch les messages
              console.log(`[SSE DEBUG] 🔄 Tool call updated - triggering refetch`)
              callbacks.onRefetchMessages()
              break

            case 'stopped':
            case 'done':
              console.log(`[SSE DEBUG] 🏁 Stream ${eventType} event received`)
              callbacks.onDone()
              return // Terminer le stream

            case 'error':
              console.log(`[SSE DEBUG] ❌ Stream error event: ${data.message}`)
              callbacks.onError(data.message || 'Unknown error')
              return // Terminer le stream

            default:
              console.warn('[SSE] Unknown event type:', eventType, data)
          }
        }
      }

      // Si on sort de la boucle sans event "done", appeler onDone
      console.log(`[SSE DEBUG] 🏁 Stream ended naturally (no done event)`)
      callbacks.onDone()
    } catch (error: any) {
      const errorTime = Date.now() - streamStartTime

      // Vérifier si c'est un 409 Conflict
      const isConflict = error.response?.status === 409 || error.message?.includes('409')

      if (isConflict) {
        console.log(`[SSE] 🔄 Conflict detected (generation in progress) - showing modal`)
        // NE PAS appeler callbacks.onError, juste re-throw pour modale
        throw error
      }

      // Log et callback pour autres erreurs
      console.error(`[SSE] 💥 Error after ${errorTime}ms:`, error.message || error)

      if (error.response) {
        const errorMsg = error.response.data?.detail || error.message || 'HTTP error'
        callbacks.onError(errorMsg)
      } else {
        callbacks.onError(error.message || 'Stream error')
      }
    } finally {
      const finalTime = Date.now() - streamStartTime
      console.log(`[SSE DEBUG] 🧹 Cleanup - Total stream duration: ${finalTime}ms`)
      if (reader) {
        try {
          reader.releaseLock()
          console.log(`[SSE DEBUG] ✅ Reader lock released`)
        } catch (e) {
          console.error(`[SSE DEBUG] ❌ Failed to release reader lock:`, e)
        }
      }
    }
  },
}
