import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  useChats,
  useChat,
  useMessages,
  useCreateChat,
  useDeleteChat,
  useSendMessage,
  useStreamMessage,
} from './chats.hooks'
import { chatService } from './chats.service'
import type { ReactNode } from 'react'

// Mock service
vi.mock('./chats.service', () => ({
  chatService: {
    getChats: vi.fn(),
    getChat: vi.fn(),
    getMessages: vi.fn(),
    createChat: vi.fn(),
    deleteChat: vi.fn(),
    sendMessage: vi.fn(),
    stopStream: vi.fn(),
    streamMessage: vi.fn(),
  },
  chatKeys: {
    all: ['chats'],
    lists: () => ['chats', 'list'],
    detail: (id: string) => ['chats', 'detail', id],
    messages: (chatId: string) => ['chats', chatId, 'messages'],
  },
}))

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

// Wrapper pour React Query
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('useChats', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch chats successfully', async () => {
    const mockChats = [
      {
        id: '1',
        user_id: 'user-1',
        agent_id: 'agent-1',
        title: 'Chat 1',
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
        team_id: null
      },
    ]

    vi.mocked(chatService.getChats).mockResolvedValue(mockChats)

    const { result } = renderHook(() => useChats(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockChats)
    expect(chatService.getChats).toHaveBeenCalledOnce()
  })

  it('should handle loading state', () => {
    vi.mocked(chatService.getChats).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    const { result } = renderHook(() => useChats(), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('should handle error state', async () => {
    vi.mocked(chatService.getChats).mockRejectedValue(new Error('API Error'))

    const { result } = renderHook(() => useChats(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBeDefined()
  })
})

describe('useChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch chat when ID is provided', async () => {
    const mockChat = {
      id: '1',
      user_id: 'user-1',
      agent_id: 'agent-1',
      title: 'Chat 1',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
      team_id: null
    }

    vi.mocked(chatService.getChat).mockResolvedValue(mockChat)

    const { result } = renderHook(() => useChat('1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockChat)
    expect(chatService.getChat).toHaveBeenCalledWith('1')
  })

  it('should not fetch when ID is null', () => {
    const { result } = renderHook(() => useChat(null), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.data).toBeUndefined()
    expect(chatService.getChat).not.toHaveBeenCalled()
  })
})

describe('useMessages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch messages when chatId is provided', async () => {
    const mockMessages = [
      {
        id: '1',
        chat_id: 'chat-1',
        role: 'user' as const,
        content: 'Hello',
        created_at: '2024-01-01',
        metadata: null
      },
    ]

    vi.mocked(chatService.getMessages).mockResolvedValue(mockMessages)

    const { result } = renderHook(() => useMessages('chat-1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockMessages)
    expect(chatService.getMessages).toHaveBeenCalledWith('chat-1', 100)
  })

  it('should not fetch when chatId is null', () => {
    const { result } = renderHook(() => useMessages(null), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(false)
    expect(chatService.getMessages).not.toHaveBeenCalled()
  })

  it('should fetch messages with custom limit', async () => {
    const mockMessages = [
      {
        id: '1',
        chat_id: 'chat-1',
        role: 'user' as const,
        content: 'Hello',
        created_at: '2024-01-01',
        metadata: null
      },
    ]

    vi.mocked(chatService.getMessages).mockResolvedValue(mockMessages)

    const { result } = renderHook(() => useMessages('chat-1', 50), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(chatService.getMessages).toHaveBeenCalledWith('chat-1', 50)
  })
})

describe('useCreateChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should create chat and invalidate cache', async () => {
    const dto = { agent_id: 'agent-1', title: 'New Chat' }
    const mockResponse = {
      id: 'new-123',
      user_id: 'user-1',
      ...dto,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
      team_id: null
    }

    vi.mocked(chatService.createChat).mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useCreateChat(), {
      wrapper: createWrapper(),
    })

    result.current.mutate(dto)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(chatService.createChat).toHaveBeenCalledWith(dto)
    expect(result.current.data).toEqual(mockResponse)
  })
})

describe('useDeleteChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should delete chat and invalidate cache', async () => {
    vi.mocked(chatService.deleteChat).mockResolvedValue()

    const { result } = renderHook(() => useDeleteChat(), {
      wrapper: createWrapper(),
    })

    result.current.mutate('chat-123')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(chatService.deleteChat).toHaveBeenCalledWith('chat-123')
  })
})

describe('useSendMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should send message when chatId is provided', async () => {
    const dto = { message: 'Hello' }
    const mockResponse = {
      id: 'msg-1',
      chat_id: 'chat-1',
      role: 'user' as const,
      content: 'Hello',
      created_at: '2024-01-01',
      metadata: null
    }

    vi.mocked(chatService.sendMessage).mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useSendMessage('chat-1'), {
      wrapper: createWrapper(),
    })

    result.current.mutate(dto)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(chatService.sendMessage).toHaveBeenCalledWith('chat-1', dto)
    expect(result.current.data).toEqual(mockResponse)
  })

  it('should throw error when chatId is null', async () => {
    const dto = { message: 'Hello' }

    const { result } = renderHook(() => useSendMessage(null), {
      wrapper: createWrapper(),
    })

    result.current.mutate(dto)

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBeDefined()
    expect((result.current.error as Error).message).toBe('Chat ID required')
  })
})

describe('useStreamMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should stream message and update states', async () => {
    vi.mocked(chatService.streamMessage).mockImplementation(
      async (chatId, request, callbacks) => {
        // Simuler des chunks SSE
        callbacks.onChunk('Hello')
        callbacks.onChunk(' World')
        callbacks.onDone()
      }
    )

    const { result } = renderHook(() => useStreamMessage('chat-1'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isStreaming).toBe(false)
    expect(result.current.currentMessage).toBe('')

    await result.current.streamMessage('Test message')

    await waitFor(() => expect(result.current.isStreaming).toBe(false))

    expect(result.current.currentMessage).toBe('Hello World')
  })

  it('should not stream if chatId is null', async () => {
    const { result } = renderHook(() => useStreamMessage(null), {
      wrapper: createWrapper(),
    })

    await result.current.streamMessage('Test')

    expect(chatService.streamMessage).not.toHaveBeenCalled()
  })

  it('should handle sources event', async () => {
    const mockSources = [
      { title: 'Source 1', url: 'http://example.com/1', score: 0.9 },
      { title: 'Source 2', url: 'http://example.com/2', score: 0.8 },
    ]

    vi.mocked(chatService.streamMessage).mockImplementation(
      async (chatId, request, callbacks) => {
        callbacks.onChunk('Test')
        callbacks.onSources(mockSources)
        callbacks.onDone()
      }
    )

    const { result } = renderHook(() => useStreamMessage('chat-1'), {
      wrapper: createWrapper(),
    })

    await result.current.streamMessage('Test message')

    await waitFor(() => expect(result.current.sources).toEqual(mockSources))
  })

  it('should handle validation required event', async () => {
    const mockValidationId = 'val-123'
    const onValidationRequired = vi.fn()

    vi.mocked(chatService.streamMessage).mockImplementation(
      async (chatId, request, callbacks) => {
        callbacks.onChunk('Test')
        callbacks.onValidationRequired?.(mockValidationId)
        callbacks.onDone()
      }
    )

    const { result } = renderHook(() => useStreamMessage('chat-1'), {
      wrapper: createWrapper(),
    })

    await result.current.streamMessage('Test message', undefined, onValidationRequired)

    await waitFor(() => {
      expect(onValidationRequired).toHaveBeenCalledWith(mockValidationId)
    })
  })

  it('should stop stream', async () => {
    vi.mocked(chatService.stopStream).mockResolvedValue()

    const { result } = renderHook(() => useStreamMessage('chat-1'), {
      wrapper: createWrapper(),
    })

    await result.current.stopStream()

    expect(chatService.stopStream).toHaveBeenCalledWith('chat-1')
  })

  it('should not stop stream if chatId is null', async () => {
    const { result } = renderHook(() => useStreamMessage(null), {
      wrapper: createWrapper(),
    })

    await result.current.stopStream()

    expect(chatService.stopStream).not.toHaveBeenCalled()
  })
})
