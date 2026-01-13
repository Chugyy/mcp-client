# Plan de tests - Service Chats Frontend

## Vue d'ensemble
Ce document décrit la stratégie de tests pour le service chats frontend (React Query + SSE).

## Tests unitaires

### chats.service.test.ts
**Fichier testé** : `src/services/chats/chats.service.ts`

- [ ] `test_parse_sse_events()` - Vérifie parsing SSE correct
- [ ] `test_buffer_incomplete_events()` - Vérifie gestion buffer SSE
- [ ] `test_handle_chunk_event()` - Callback onChunk appelé
- [ ] `test_handle_validation_required_event()` - Callback onValidationRequired appelé
- [ ] `test_handle_sources_event()` - Callback onSources appelé
- [ ] `test_handle_error_event()` - Callback onError appelé
- [ ] `test_handle_done_event()` - Callback onDone appelé
- [ ] `test_handle_stopped_event()` - Stream arrêté correctement
- [ ] `test_stream_with_malformed_sse()` - Gestion erreur parsing
- [ ] `test_chat_keys_structure()` - Vérifie query keys correctes

### chats.hooks.test.ts
**Fichier testé** : `src/services/chats/chats.hooks.ts`

- [ ] `test_useChats_fetch()` - Récupère liste des chats
- [ ] `test_useChats_loading_state()` - État loading correct
- [ ] `test_useChats_error_state()` - Gestion erreur
- [ ] `test_useChat_fetch()` - Récupère un chat par ID
- [ ] `test_useChat_disabled_when_no_id()` - Désactivé si pas d'ID
- [ ] `test_useMessages_fetch()` - Récupère messages
- [ ] `test_useMessages_with_limit()` - Pagination
- [ ] `test_useCreateChat_mutation()` - Création chat
- [ ] `test_useCreateChat_invalidates_queries()` - Invalidation cache
- [ ] `test_useDeleteChat_mutation()` - Suppression chat
- [ ] `test_useDeleteChat_optimistic_update()` - Update optimiste
- [ ] `test_useStopStream_mutation()` - Arrêt stream
- [ ] `test_useStreamMessage_streaming()` - Stream message
- [ ] `test_useStreamMessage_error_handling()` - Gestion erreur stream
- [ ] `test_useStreamMessage_cleanup_on_unmount()` - Cleanup React

## Tests d'intégration

### chat-context.test.tsx
**Fichier testé** : `src/contexts/chat-context.tsx`

- [ ] `test_context_provides_chats()` - Fournit liste chats
- [ ] `test_context_provides_messages()` - Fournit messages
- [ ] `test_context_stream_message()` - Stream message via context
- [ ] `test_context_create_chat()` - Créer chat via context
- [ ] `test_context_delete_chat()` - Supprimer chat via context
- [ ] `test_context_selected_agent_state()` - État agent sélectionné
- [ ] `test_context_selected_model_state()` - État modèle sélectionné
- [ ] `test_context_active_chat_id_state()` - État chat actif

### chat-input.test.tsx
**Fichier testé** : `src/components/chat/chat-input.tsx`

- [ ] `test_input_sends_message()` - Envoi message
- [ ] `test_input_disabled_while_streaming()` - Désactivé pendant stream
- [ ] `test_input_clears_after_send()` - Nettoyage après envoi
- [ ] `test_input_requires_agent_selection()` - Requiert agent
- [ ] `test_input_shows_model_selector()` - Sélecteur modèle affiché

### chat-messages.test.tsx
**Fichier testé** : `src/components/chat/chat-messages.tsx`

- [ ] `test_displays_messages()` - Affiche messages
- [ ] `test_displays_sources_metadata()` - Affiche sources si metadata
- [ ] `test_renders_markdown()` - Rendu markdown correct
- [ ] `test_loading_state()` - État chargement
- [ ] `test_empty_state()` - État vide

## Tests E2E (Playwright)

### chat.spec.ts
**Scénarios utilisateur**

- [ ] `test_create_chat_and_stream_message()` - Créer chat + message
- [ ] `test_validation_flow()` - Flow validation complet
- [ ] `test_stop_stream()` - Arrêt stream via bouton
- [ ] `test_sources_display()` - Affichage sources
- [ ] `test_multiple_messages_conversation()` - Conversation multi-messages
- [ ] `test_delete_chat()` - Suppression chat
- [ ] `test_switch_between_chats()` - Basculer entre chats

### validation.spec.ts
**Tests validation UI**

- [ ] `test_validation_modal_appears()` - Modal validation apparaît
- [ ] `test_approve_validation()` - Approuver validation
- [ ] `test_reject_validation()` - Rejeter validation
- [ ] `test_feedback_validation()` - Donner feedback

## Configuration tests

### vitest.config.ts
```typescript
export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/services/chats/**'],
      exclude: ['**/*.test.ts', '**/*.spec.ts']
    }
  }
})
```

### setup.ts
```typescript
import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Cleanup après chaque test
afterEach(() => {
  cleanup()
})

// Mock fetch
global.fetch = vi.fn()
```

## Fixtures et helpers

### test-utils.tsx
```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  })
}

export function renderWithProviders(ui: ReactNode) {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  )
}
```

### mock-sse.ts
```typescript
export class MockSSEStream {
  constructor(private events: Array<{type: string, data: any}>) {}

  async *[Symbol.asyncIterator]() {
    for (const event of this.events) {
      yield `event: ${event.type}\ndata: ${JSON.stringify(event.data)}\n\n`
    }
  }
}
```

## Couverture cible
- **services/chats/** : 95%
- **components/chat/** : 85%
- **contexts/chat-context.tsx** : 90%
- **Global nouveau code** : 90%

## Commandes

```bash
# Tous les tests
npm test

# Tests unitaires
npm test -- --grep "\.test\.ts$"

# Tests composants
npm test -- --grep "\.test\.tsx$"

# Avec coverage
npm test -- --coverage

# Mode watch
npm test -- --watch

# E2E
npm run test:e2e

# Un seul fichier
npm test src/services/chats/chats.service.test.ts
```

## Notes importantes

1. **SSE Mocking** : Utiliser `ReadableStream` pour simuler SSE
2. **React Query** : Toujours wrapper avec `QueryClientProvider` dans les tests
3. **Async** : Utiliser `waitFor` de `@testing-library/react` pour les updates async
4. **Cleanup** : Utiliser `cleanup()` après chaque test
5. **TypeScript** : Tests 100% typés
