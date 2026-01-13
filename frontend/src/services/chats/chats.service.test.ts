import { describe, it, expect, vi, beforeEach } from 'vitest'
import { chatService, chatKeys } from './chats.service'
import { apiClient } from '@/lib/api-client'
import type { Chat, Message, ChatCreate, MessageCreate, Source } from './chats.types'

// Mock apiClient
vi.mock('@/lib/api-client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('chatKeys', () => {
  it('should generate correct query keys structure', () => {
    expect(chatKeys.all).toEqual(['chats'])
    expect(chatKeys.lists()).toEqual(['chats', 'list'])
    expect(chatKeys.detail('chat-123')).toEqual(['chats', 'detail', 'chat-123'])
    expect(chatKeys.messages('chat-123')).toEqual(['chats', 'chat-123', 'messages'])
  })
})

describe('chatService.getChats', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch all chats', async () => {
    const mockChats: Chat[] = [
      {
        id: '1',
        user_id: 'user-1',
        agent_id: 'agent-1',
        team_id: null,
        title: 'Chat 1',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
      {
        id: '2',
        user_id: 'user-1',
        agent_id: 'agent-2',
        team_id: null,
        title: 'Chat 2',
        created_at: '2024-01-02T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
      },
    ]

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockChats })

    const result = await chatService.getChats()

    expect(apiClient.get).toHaveBeenCalledWith('/chats')
    expect(result).toEqual(mockChats)
  })
})

describe('chatService.getChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch a single chat by ID', async () => {
    const mockChat: Chat = {
      id: '1',
      user_id: 'user-1',
      agent_id: 'agent-1',
      team_id: null,
      title: 'Chat 1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockChat })

    const result = await chatService.getChat('1')

    expect(apiClient.get).toHaveBeenCalledWith('/chats/1')
    expect(result).toEqual(mockChat)
  })
})

describe('chatService.createChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should create a new chat', async () => {
    const dto: ChatCreate = { agent_id: 'agent-1', title: 'New Chat' }
    const mockResponse: Chat = {
      id: 'new-123',
      user_id: 'user-1',
      agent_id: 'agent-1',
      team_id: null,
      title: 'New Chat',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse })

    const result = await chatService.createChat(dto)

    expect(apiClient.post).toHaveBeenCalledWith('/chats', dto)
    expect(result).toEqual(mockResponse)
  })
})

describe('chatService.deleteChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should delete a chat', async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({})

    await chatService.deleteChat('chat-123')

    expect(apiClient.delete).toHaveBeenCalledWith('/chats/chat-123')
  })
})

describe('chatService.getMessages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch messages with default limit', async () => {
    const mockMessages: Message[] = [
      {
        id: '1',
        chat_id: 'chat-1',
        role: 'user',
        content: 'Hello',
        created_at: '2024-01-01T00:00:00Z',
      },
      {
        id: '2',
        chat_id: 'chat-1',
        role: 'assistant',
        content: 'Hi',
        created_at: '2024-01-02T00:00:00Z',
      },
    ]

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockMessages })

    const result = await chatService.getMessages('chat-1')

    expect(apiClient.get).toHaveBeenCalledWith('/chats/chat-1/messages', {
      params: { limit: 100 },
    })
    expect(result).toEqual(mockMessages)
  })

  it('should fetch messages with custom limit', async () => {
    const mockMessages: Message[] = []

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockMessages })

    await chatService.getMessages('chat-1', 50)

    expect(apiClient.get).toHaveBeenCalledWith('/chats/chat-1/messages', {
      params: { limit: 50 },
    })
  })
})

describe('chatService.sendMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should send a message', async () => {
    const dto: MessageCreate = { role: 'user', content: 'Hello' }
    const mockResponse: Message = {
      id: 'msg-123',
      chat_id: 'chat-1',
      role: 'user',
      content: 'Hello',
      created_at: '2024-01-01T00:00:00Z',
    }

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse })

    const result = await chatService.sendMessage('chat-1', dto)

    expect(apiClient.post).toHaveBeenCalledWith('/chats/chat-1/messages', dto)
    expect(result).toEqual(mockResponse)
  })
})

describe('chatService.stopStream', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should stop a stream', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({})

    await chatService.stopStream('chat-123')

    expect(apiClient.post).toHaveBeenCalledWith('/chats/chat-123/stop')
  })
})

describe('chatService.streamMessage - SSE Parser', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  /**
   * Helper pour créer un mock stream SSE
   */
  function createMockSSEStream(sseData: string) {
    const encoder = new TextEncoder()
    const chunks = [encoder.encode(sseData)]
    let index = 0

    const mockReader = {
      read: vi.fn(async () => {
        if (index < chunks.length) {
          const chunk = chunks[index++]
          const decoder = new TextDecoder()
          return { done: false, value: decoder.decode(chunk) }
        }
        return { done: true, value: undefined }
      }),
      releaseLock: vi.fn(),
    }

    const mockStream = {
      pipeThrough: vi.fn(() => ({
        getReader: vi.fn(() => mockReader),
      })),
    }

    return { mockStream, mockReader }
  }

  it('should parse SSE events and call callbacks', async () => {
    const sseData = `event: chunk
data: {"content":"Hello"}

event: chunk
data: {"content":" World"}

event: sources
data: {"sources":[{"resource_id":"res-1","resource_name":"Doc 1","chunk_id":"chunk-1","similarity":0.9,"content":"Some content"}]}

event: done
data: {}
`

    const { mockStream, mockReader } = createMockSSEStream(sseData)

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    expect(callbacks.onChunk).toHaveBeenCalledWith('Hello')
    expect(callbacks.onChunk).toHaveBeenCalledWith(' World')
    expect(callbacks.onSources).toHaveBeenCalledWith([
      {
        resource_id: 'res-1',
        resource_name: 'Doc 1',
        chunk_id: 'chunk-1',
        similarity: 0.9,
        content: 'Some content',
      },
    ])
    expect(callbacks.onDone).toHaveBeenCalled()
    expect(mockReader.releaseLock).toHaveBeenCalled()
  })

  it('should handle malformed SSE events gracefully', async () => {
    const sseData = `event: chunk
data: {"content":"Valid"}

malformed line without event

data: {"content":"Orphan data"}

event: chunk
invalid data line

event: done
data: {}
`

    const { mockStream, mockReader } = createMockSSEStream(sseData)

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    // Capturer les console.warn pour vérifier qu'ils sont appelés
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    // Should have called onChunk for valid event only
    expect(callbacks.onChunk).toHaveBeenCalledTimes(1)
    expect(callbacks.onChunk).toHaveBeenCalledWith('Valid')

    // Should have called onDone
    expect(callbacks.onDone).toHaveBeenCalled()

    // Should not have called onError (malformed events are ignored)
    expect(callbacks.onError).not.toHaveBeenCalled()

    // Should have logged warnings for malformed events
    expect(consoleWarnSpy).toHaveBeenCalled()

    consoleWarnSpy.mockRestore()
  })

  it('should handle stream errors', async () => {
    const mockReader = {
      read: vi.fn().mockRejectedValue(new Error('Stream error')),
      releaseLock: vi.fn(),
    }

    const mockStream = {
      pipeThrough: vi.fn(() => ({
        getReader: vi.fn(() => mockReader),
      })),
    }

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    // Capturer console.error pour éviter le bruit
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    expect(callbacks.onError).toHaveBeenCalledWith('Stream error')
    expect(mockReader.releaseLock).toHaveBeenCalled()

    consoleErrorSpy.mockRestore()
  })

  it('should handle validation_required event', async () => {
    const sseData = `event: validation_required
data: {"validation_id":"val-123"}

event: done
data: {}
`

    const { mockStream, mockReader } = createMockSSEStream(sseData)

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    expect(callbacks.onValidationRequired).toHaveBeenCalledWith('val-123')
    expect(callbacks.onDone).toHaveBeenCalled()
    expect(mockReader.releaseLock).toHaveBeenCalled()
  })

  it('should handle stopped event', async () => {
    const sseData = `event: chunk
data: {"content":"Start"}

event: stopped
data: {}
`

    const { mockStream, mockReader } = createMockSSEStream(sseData)

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    expect(callbacks.onChunk).toHaveBeenCalledWith('Start')
    expect(callbacks.onDone).toHaveBeenCalled()
    expect(mockReader.releaseLock).toHaveBeenCalled()
  })

  it('should handle error event', async () => {
    const sseData = `event: chunk
data: {"content":"Start"}

event: error
data: {"message":"Something went wrong"}
`

    const { mockStream, mockReader } = createMockSSEStream(sseData)

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    // Capturer console.error pour éviter le bruit
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    expect(callbacks.onChunk).toHaveBeenCalledWith('Start')
    expect(callbacks.onError).toHaveBeenCalledWith('Something went wrong')
    expect(callbacks.onDone).not.toHaveBeenCalled()
    expect(mockReader.releaseLock).toHaveBeenCalled()

    consoleErrorSpy.mockRestore()
  })

  it('should handle JSON parsing errors in SSE data', async () => {
    const sseData = `event: chunk
data: invalid json

event: done
data: {}
`

    const { mockStream, mockReader } = createMockSSEStream(sseData)

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    // Capturer console.error pour éviter le bruit
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    // Should not have called onChunk (invalid JSON)
    expect(callbacks.onChunk).not.toHaveBeenCalled()

    // Should have called onDone
    expect(callbacks.onDone).toHaveBeenCalled()

    // Should have logged error for invalid JSON
    expect(consoleErrorSpy).toHaveBeenCalled()

    consoleErrorSpy.mockRestore()
  })

  it('should handle missing content field in chunk event', async () => {
    const sseData = `event: chunk
data: {"wrong_field":"value"}

event: done
data: {}
`

    const { mockStream, mockReader } = createMockSSEStream(sseData)

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    // Capturer console.warn pour vérifier
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    // Should not have called onChunk (missing content field)
    expect(callbacks.onChunk).not.toHaveBeenCalled()

    // Should have called onDone
    expect(callbacks.onDone).toHaveBeenCalled()

    // Should have logged warning
    expect(consoleWarnSpy).toHaveBeenCalled()

    consoleWarnSpy.mockRestore()
  })

  it('should handle missing sources array in sources event', async () => {
    const sseData = `event: sources
data: {"wrong_field":"value"}

event: done
data: {}
`

    const { mockStream, mockReader } = createMockSSEStream(sseData)

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    // Capturer console.warn pour vérifier
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    // Should not have called onSources (missing sources array)
    expect(callbacks.onSources).not.toHaveBeenCalled()

    // Should have called onDone
    expect(callbacks.onDone).toHaveBeenCalled()

    // Should have logged warning
    expect(consoleWarnSpy).toHaveBeenCalled()

    consoleWarnSpy.mockRestore()
  })

  it('should handle missing validation_id in validation_required event', async () => {
    const sseData = `event: validation_required
data: {"wrong_field":"value"}

event: done
data: {}
`

    const { mockStream, mockReader } = createMockSSEStream(sseData)

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    // Capturer console.warn pour vérifier
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    // Should not have called onValidationRequired (missing validation_id)
    expect(callbacks.onValidationRequired).not.toHaveBeenCalled()

    // Should have called onDone
    expect(callbacks.onDone).toHaveBeenCalled()

    // Should have logged warning
    expect(consoleWarnSpy).toHaveBeenCalled()

    consoleWarnSpy.mockRestore()
  })

  it('should handle unknown event types', async () => {
    const sseData = `event: unknown_event
data: {"field":"value"}

event: done
data: {}
`

    const { mockStream, mockReader } = createMockSSEStream(sseData)

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockStream })

    const callbacks = {
      onChunk: vi.fn(),
      onSources: vi.fn(),
      onValidationRequired: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn(),
    }

    // Capturer console.warn pour vérifier
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    await chatService.streamMessage('chat-1', { message: 'Test' }, callbacks)

    // Should not have called any callbacks except onDone
    expect(callbacks.onChunk).not.toHaveBeenCalled()
    expect(callbacks.onSources).not.toHaveBeenCalled()
    expect(callbacks.onValidationRequired).not.toHaveBeenCalled()
    expect(callbacks.onError).not.toHaveBeenCalled()
    expect(callbacks.onDone).toHaveBeenCalled()

    // Should have logged warning for unknown event
    expect(consoleWarnSpy).toHaveBeenCalled()

    consoleWarnSpy.mockRestore()
  })
})
