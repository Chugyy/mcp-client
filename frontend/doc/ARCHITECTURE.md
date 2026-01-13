# Architecture Frontend

## Vue d'ensemble

Application Next.js 16 (App Router) avec React 19, TypeScript, et authentification par cookies httpOnly.

**Stack complète** :
- **Framework** : Next.js 16 (App Router) + React 19
- **Styling** : Tailwind CSS 4
- **UI Components** : shadcn/ui (Radix UI + Tailwind)
- **State Management** : React Query 5 + Context API
- **Forms** : React Hook Form + Zod
- **HTTP Client** : Axios avec interceptors
- **Theme** : next-themes (dark/light mode)

---

## 1. Architecture des fichiers

```
src/
├── app/                    # Next.js App Router
│   ├── (auth)/            # Routes publiques (login, forgot-password)
│   │   ├── login/page.tsx
│   │   ├── forgot-password/page.tsx
│   │   └── layout.tsx
│   │
│   ├── (protected)/       # Routes protégées (dashboard, chat, agents, etc.)
│   │   ├── dashboard/page.tsx
│   │   ├── chat/[conversationId]/page.tsx
│   │   ├── agents/page.tsx
│   │   ├── automatisations/page.tsx
│   │   ├── mcp-tools/page.tsx
│   │   ├── ressources/page.tsx
│   │   ├── validation/page.tsx
│   │   ├── settings/page.tsx
│   │   ├── page.tsx      # Home (redirige vers premier chat)
│   │   └── layout.tsx     # Layout protégé (ChatProvider + Sidebar)
│   │
│   ├── layout.tsx         # Root layout (Providers globaux)
│   └── globals.css
│
├── components/            # Composants réutilisables
│   ├── layouts/          # Layouts (sidebar, header, app-layout)
│   │   ├── sidebar.tsx
│   │   ├── header.tsx
│   │   ├── app-layout.tsx
│   │   └── entity-list-page.tsx
│   ├── navigation/       # Navigation (nav-menu, user-dropdown)
│   ├── chat/            # Interface de chat
│   ├── agents/          # Gestion des agents
│   ├── resources/       # Ressources RAG
│   ├── mcp/             # Outils MCP
│   ├── validation/      # Tâches de validation
│   ├── user/            # Profil utilisateur
│   └── ui/              # Primitives UI (shadcn/ui + custom)
│       └── shadcn-io/   # Composants shadcn avancés (AI, code-block)
│
├── contexts/             # State global
│   └── chat-context.tsx  # Context principal (auth, agents, chats, messages)
│
├── services/             # Services API (architecture modulaire)
│   ├── auth/
│   │   ├── auth.service.ts   # Appels API
│   │   ├── auth.hooks.ts     # Hooks React Query
│   │   ├── auth.types.ts     # Types TypeScript
│   │   └── auth.refresh.ts   # Logique refresh token
│   ├── agents/
│   │   ├── agents.service.ts
│   │   ├── agents.hooks.ts
│   │   └── agents.types.ts
│   ├── chats/
│   │   ├── chats.service.ts
│   │   ├── chats.hooks.ts
│   │   └── chats.types.ts
│   ├── resources/
│   ├── mcp/
│   ├── validations/
│   ├── providers/
│   └── api-keys/
│
├── hooks/                # Custom hooks utilitaires
│   ├── use-file-upload.ts
│   ├── use-agents.ts
│   └── use-mobile.ts
│
├── lib/                  # Utilitaires
│   ├── api-client.ts    # Instance Axios + QueryClient
│   └── api.ts           # Types API (DEPRECATED - migration vers services/)
│
├── types/                # Types TypeScript globaux
│   └── api.types.ts
│
└── middleware.ts         # Middleware Next.js (protection routes + redirections)
```

---

## 2. L'application

### Routes

**Routes publiques** (accessible sans auth):
- `/login` - Connexion
- `/forgot-password` - Réinitialisation mot de passe

**Routes protégées** (nécessite auth):
- `/` - Home (redirige vers premier chat)
- `/dashboard` - Tableau de bord
- `/chat/[conversationId]` - Interface de chat
- `/agents` - Gestion des agents et teams
- `/automatisations` - Automatisations
- `/mcp-tools` - Configuration MCP
- `/ressources` - Ressources RAG
- `/validation` - Tâches de validation
- `/settings` - Paramètres utilisateur

### State Management

L'application combine deux approches complémentaires :

#### 1. React Query (TanStack Query v5)

**Configuration globale** (`/src/lib/api-client.ts:60`):
```typescript
queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,                           // 1 tentative en cas d'échec
      staleTime: 5 * 60 * 1000,          // 5 minutes avant considérer stale
      refetchOnWindowFocus: false,        // Pas de refetch au focus
    },
    mutations: {
      retry: 0,                           // Pas de retry pour mutations
    },
  },
})
```

**Architecture modulaire des services** :

Chaque domaine métier suit le pattern :
- `*.service.ts` : Fonctions d'appel API (avec apiClient Axios)
- `*.hooks.ts` : Hooks React Query (useQuery, useMutation)
- `*.types.ts` : Types TypeScript

Exemple pour `agents/` :
```typescript
// agents.service.ts
export const agentsService = {
  getAll: () => apiClient.get('/agents'),
  create: (dto, avatar?) => apiClient.post('/agents', dto),
  update: (id, dto, avatar?) => apiClient.patch(`/agents/${id}`, dto),
  // ...
}

export const agentKeys = {
  all: ['agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  detail: (id: string) => [...agentKeys.all, 'detail', id] as const,
}

// agents.hooks.ts
export function useAgents() {
  return useQuery({
    queryKey: agentKeys.lists(),
    queryFn: agentsService.getAll,
  })
}

export function useUpdateAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data, avatar }) =>
      agentsService.update(id, data, avatar),

    // Optimistic update
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: agentKeys.lists() })
      const previousData = queryClient.getQueryData(agentKeys.lists())

      queryClient.setQueryData(agentKeys.lists(), (old) =>
        old.map((item) => (item.id === id ? { ...item, ...data } : item))
      )

      return { previousData }
    },

    // Invalidation du cache
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
      toast.success('Agent mis à jour')
    },

    // Rollback en cas d'erreur
    onError: (_, __, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(agentKeys.lists(), context.previousData)
      }
      toast.error('Erreur')
    },
  })
}
```

**Patterns clés** :
- **Query keys hiérarchiques** : `['agents', 'list']` vs `['agents', 'detail', id]`
- **Optimistic updates** : Mise à jour immédiate du cache avant la réponse serveur
- **Invalidation automatique** : `invalidateQueries()` après mutations pour refetch
- **Error handling** : Rollback automatique avec `onError` + contexte
- **Toast notifications** : Feedback utilisateur systématique

#### 2. Context API - ChatContext

**Responsabilité** (`/src/contexts/chat-context.tsx`) :
- Agrège les données de plusieurs hooks React Query
- Fournit des fonctions métier de haut niveau
- Gère l'état local UI (activeChatId, isSending, optimisticUserMessage)

**Données exposées** :
```typescript
interface ChatContextType {
  // Auth
  logout: () => void

  // Agents (de useAgents hook)
  agents: Agent[]
  agentsLoading: boolean

  // Chats (de useChats hook)
  chats: Chat[]
  chatsLoading: boolean
  refetchChats: () => void

  // Chat actif (état local)
  activeChatId: string | null
  activeChat: Chat | null
  setActiveChatId: (id: string | null) => void

  // Messages (de useMessages + useStreamMessage hooks)
  messages: Message[]
  messagesLoading: boolean
  streaming: boolean
  isSending: boolean
  streamingMessage: string
  sources: Source[]
  pendingValidation: string | null

  // Actions métier
  sendMessage: (content, model, agentId) => Promise<void>
  stopStream: () => Promise<void>
  createNewChat: () => Promise<void>
  createChatWithParams: (params) => Promise<void>
  deleteChat: (chatId: string) => Promise<void>
}
```

**Logique métier encapsulée** :
- **Optimistic UI** : Affiche le message utilisateur avant la réponse serveur
- **Streaming SSE** : Gère le flux en temps réel avec `useStreamMessage()`
- **Navigation automatique** : Redirige vers le nouveau chat après création
- **Cleanup** : Nettoie les états locaux après stop/erreur

---

## 3. Interaction Backend & Authentification

### Architecture HTTP Client

**Configuration Axios** (`/src/lib/api-client.ts:10`) :
```typescript
export const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
  withCredentials: true,  // CRITIQUE : Envoie automatiquement les cookies
})
```

Le `withCredentials: true` permet :
- Envoi automatique des cookies httpOnly à chaque requête
- Réception des Set-Cookie headers du backend
- Pas de gestion manuelle des tokens en JavaScript

**Interceptor Response** (`/src/lib/api-client.ts:23`) :
```typescript
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Si 401 et requête pas déjà retryée
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Éviter de refresh sur les endpoints d'auth
      if (originalRequest.url?.includes('/auth/login') ||
          originalRequest.url?.includes('/auth/register') ||
          originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error)
      }

      originalRequest._retry = true

      try {
        const { refreshAccessToken } = await import('@/services/auth/auth.refresh')
        await refreshAccessToken()  // POST /auth/refresh
        return apiClient(originalRequest)  // Retry la requête originale
      } catch (refreshError) {
        // Redirect vers /login géré dans auth.refresh.ts
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)
```

**Logique de refresh** (`/src/services/auth/auth.refresh.ts:15`) :
```typescript
let isRefreshing = false
let refreshPromise: Promise<void> | null = null

export async function refreshAccessToken(): Promise<void> {
  // Si refresh déjà en cours, retourner la même promesse (évite les appels multiples)
  if (isRefreshing && refreshPromise) {
    return refreshPromise
  }

  isRefreshing = true
  refreshPromise = apiClient
    .post('/auth/refresh')  // Utilise le refresh_token cookie
    .then(() => {
      // access_token cookie mis à jour par le backend
      console.log('[Auth] Access token refreshed successfully')
    })
    .catch((error) => {
      // Refresh échoué → redirect login
      console.error('[Auth] Failed to refresh token:', error)
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
      throw error
    })
    .finally(() => {
      isRefreshing = false
      refreshPromise = null
    })

  return refreshPromise
}
```

### Stratégie d'authentification

**Cookies httpOnly** (gérés côté backend) :
- `access_token` : Token d'accès JWT courte durée (ex: 15min)
- `refresh_token` : Token de rafraîchissement longue durée (ex: 7 jours)
- Attributs : `HttpOnly`, `Secure`, `SameSite=Strict`
- **Avantages** :
  - Protection contre XSS (inaccessibles en JavaScript)
  - Pas de stockage local de credentials
  - Refresh transparent pour l'utilisateur

### Service d'authentification

**auth.service.ts** (`/src/services/auth/auth.service.ts`) :
```typescript
export const authService = {
  async login(dto: LoginDTO): Promise<AuthResponse> {
    const { data } = await apiClient.post('/auth/login', dto)
    // Cookies set automatiquement par backend via Set-Cookie header
    return data
  },

  async register(dto: RegisterDTO): Promise<AuthResponse> {
    const { data } = await apiClient.post('/auth/register', dto)
    return data
  },

  async getMe(): Promise<User> {
    const { data } = await apiClient.get('/auth/me')
    return data
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout')
    // Cookies cleared par backend
  },
}
```

**auth.hooks.ts** (`/src/services/auth/auth.hooks.ts`) :
```typescript
export function useMe() {
  return useQuery({
    queryKey: ['user', 'me'],
    queryFn: authService.getMe,
    retry: false,  // Pas de retry si 401 (non authentifié)
  })
}

export function useLogin() {
  return useMutation({
    mutationFn: (dto: LoginDTO) => authService.login(dto),
    onSuccess: () => {
      toast.success('Connexion réussie')
      // Cookies déjà set, pas de stockage local
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => authService.logout(),
    onSuccess: () => {
      queryClient.clear()  // Clear TOUT le cache React Query
      toast.success('Déconnexion réussie')
      window.location.href = '/login'
    },
  })
}
```

### Middleware de protection de routes

**middleware.ts** (`/src/middleware.ts:7`) :
```typescript
const publicRoutes = ['/login', '/forgot-password']

export function middleware(request: NextRequest) {
  const accessToken = request.cookies.get('access_token')
  const isPublicRoute = publicRoutes.some(route =>
    request.nextUrl.pathname.startsWith(route)
  )

  // Route protégée sans token → redirect login
  if (!accessToken && !isPublicRoute) {
    const loginUrl = new URL('/login', request.url)
    return NextResponse.redirect(loginUrl)
  }

  // Token présent sur page login → redirect home
  if (accessToken && request.nextUrl.pathname === '/login') {
    const homeUrl = new URL('/', request.url)
    return NextResponse.redirect(homeUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    // Toutes les routes sauf api, _next/static, _next/image, favicon.ico
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
```

### Flow d'authentification complet

**1. Login** :
```
User submit form → useLogin.mutate({ email, password })
                → POST /api/v1/auth/login
                → Backend vérifie credentials
                → Backend set cookies (Set-Cookie: access_token=...; HttpOnly)
                → Frontend reçoit { user } dans response.data
                → Redirect vers /dashboard
```

**2. Requête API protégée** :
```
Component → useAgents()
         → apiClient.get('/agents')
         → Browser envoie automatiquement cookie access_token (withCredentials)
         → Backend vérifie JWT dans cookie
         → Return data si valide
```

**3. Token expiré (refresh automatique)** :
```
Component → useAgents()
         → apiClient.get('/agents')
         → 401 Unauthorized
         → Interceptor détecte 401
         → refreshAccessToken()
            → POST /auth/refresh (avec refresh_token cookie)
            → Backend vérifie refresh_token
            → Backend set nouveau access_token cookie
         → Retry apiClient.get('/agents') automatiquement
         → Success avec nouveau token
```

**4. Refresh token expiré** :
```
Interceptor → refreshAccessToken()
           → POST /auth/refresh
           → 401 Unauthorized (refresh_token invalide/expiré)
           → window.location.href = '/login'
           → User redirigé vers login
```

**5. Logout** :
```
User click logout → useLogout.mutate()
                 → POST /auth/logout
                 → Backend clear cookies (Set-Cookie: access_token=; Max-Age=0)
                 → queryClient.clear()
                 → window.location.href = '/login'
```

### Sécurité

**Protection contre les attaques** :
- **XSS** : Tokens en httpOnly cookies (inaccessibles en JS)
- **CSRF** : SameSite=Strict + vérification origin backend
- **Man-in-the-Middle** : Secure flag (HTTPS only)
- **Token theft** : Refresh automatique + courte durée access token

**Bonnes pratiques** :
- Pas de stockage de tokens en localStorage/sessionStorage
- Pas de tokens dans l'URL ou headers manipulables
- Logout complet (clear cache + cookies)
- Middleware vérifie auth avant chaque route protégée

---

## 4. Composition du Layout principal

### Root Layout (`/src/app/layout.tsx`)

```tsx
<QueryClientProvider>
  <ThemeProvider>
    <ChatProvider>
      {children}
      <Toaster />
    </ChatProvider>
  </ThemeProvider>
</QueryClientProvider>
```

Providers globaux pour:
- React Query (data fetching)
- Theme (dark/light mode)
- Chat (state global)
- Toaster (notifications)

### Layout protégé (`/src/app/(protected)/layout.tsx`)

```tsx
<SidebarProvider defaultOpen={true}>
  <Sidebar />
  {children}
</SidebarProvider>
```

Structure avec sidebar responsive et collapsible.

### Sidebar (`/src/components/layouts/sidebar.tsx`)

**Structure**:
- Logo + titre app
- NavMenu (navigation principale)
- ConversationList (historique chats)

**Navigation** (NavMenu):
- Section "Navigation": Validation, Automatisations, Agents
- Section "Construction": MCP & Outils, Ressources
- Détection active link (highlight)
- Icônes Lucide React

### Header (`/src/components/layouts/header.tsx`)

**Structure**:
- Gauche: Bouton toggle sidebar
- Droite: UserDropdown (profil, paramètres, déconnexion)

### AppLayout wrapper (`/src/components/layouts/app-layout.tsx`)

Alternative au layout protected pour pages type dashboard:
- Header avec theme toggle
- SidebarInset pour contenu full-height
- User dropdown

---

## 5. Streaming SSE (Server-Sent Events)

L'application utilise le streaming SSE pour afficher les réponses de l'IA en temps réel.

### Architecture du streaming

**Hook useStreamMessage** (`/src/services/chats/chats.hooks.ts:125`) :
```typescript
export function useStreamMessage(chatId: string | null) {
  const queryClient = useQueryClient()
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState('')
  const [sources, setSources] = useState<Source[]>([])
  const [pendingValidation, setPendingValidation] = useState<string | null>(null)

  const streamMessage = useCallback(async (
    message: string,
    model?: string,
    agentId?: string,
    onValidationRequired?: (validationId: string) => void
  ) => {
    if (!chatId) {
      toast.error('Aucun chat actif')
      return
    }

    setIsStreaming(true)
    setStreamingMessage('')
    setSources([])
    setPendingValidation(null)

    try {
      await chatService.streamMessage(chatId, { message, model, agent_id: agentId }, {
        onChunk: (content) => {
          setStreamingMessage((prev) => prev + content)  // Append streaming
        },
        onSources: (newSources) => {
          setSources(newSources)  // MAJ sources RAG
        },
        onValidationRequired: (validationId) => {
          setPendingValidation(validationId)
          onValidationRequired?.(validationId)
          setStreamingMessage('')  // Reset buffer (segment sauvegardé en DB)
          queryClient.invalidateQueries({ queryKey: chatKeys.messages(chatId) })
        },
        onError: (error) => {
          toast.error(error)
          setIsStreaming(false)
        },
        onDone: () => {
          setIsStreaming(false)
          setStreamingMessage('')
          queryClient.invalidateQueries({ queryKey: chatKeys.messages(chatId) })
          queryClient.invalidateQueries({ queryKey: chatKeys.lists() })
        },
      })
    } catch (error: any) {
      setIsStreaming(false)
      // Re-throw 409 (conflit) pour gestion par composant
      if (error.response?.status === 409 || error.message?.includes('409')) {
        throw error
      }
      toast.error(error.message || 'Erreur lors du streaming')
    }
  }, [chatId, queryClient])

  const stopStream = useCallback(async () => {
    if (!chatId) return

    try {
      await chatService.stopStream(chatId)
      setIsStreaming(false)
      setPendingValidation(null)
      toast.info('Stream arrêté')
      queryClient.invalidateQueries({ queryKey: chatKeys.messages(chatId) })
    } catch (error: any) {
      toast.error('Erreur lors de l\'arrêt du stream')
    }
  }, [chatId, queryClient])

  return {
    streamMessage,
    stopStream,
    isStreaming,
    streamingMessage,
    sources,
    pendingValidation,
  }
}
```

**Service de streaming** (`/src/services/chats/chats.service.ts`) :
```typescript
async streamMessage(
  chatId: string,
  dto: MessageCreate,
  callbacks: {
    onChunk: (content: string) => void
    onSources: (sources: Source[]) => void
    onValidationRequired: (validationId: string) => void
    onError: (error: string) => void
    onDone: () => void
  }
) {
  const response = await apiClient.post(`/chats/${chatId}/stream`, dto, {
    responseType: 'stream',
    adapter: 'fetch',
    onDownloadProgress: (progressEvent) => {
      const xhr = progressEvent.event.target
      const { responseText } = xhr

      // Parser SSE events
      const events = responseText.split('\n\n')
      for (const event of events) {
        if (event.startsWith('data: ')) {
          const data = JSON.parse(event.slice(6))

          if (data.type === 'content') {
            callbacks.onChunk(data.content)
          } else if (data.type === 'sources') {
            callbacks.onSources(data.sources)
          } else if (data.type === 'validation_required') {
            callbacks.onValidationRequired(data.validation_id)
          } else if (data.type === 'error') {
            callbacks.onError(data.error)
          } else if (data.type === 'done') {
            callbacks.onDone()
          }
        }
      }
    }
  })
}
```

**Types d'événements SSE** :
- `content` : Chunk de texte de la réponse IA
- `sources` : Sources RAG utilisées pour la réponse
- `validation_required` : Tool call nécessitant validation humaine
- `error` : Erreur lors du streaming
- `done` : Fin du streaming

**Gestion dans l'UI** :
- Buffer local (`streamingMessage`) pour affichage temps réel
- Invalidation du cache après `done` pour persister en DB
- Support arrêt manuel avec sauvegarde partielle
- Gestion des erreurs et conflits (409)

---

## 6. Patterns & Conventions

### Composants page

**Structure type** :
```typescript
'use client'  // OBLIGATOIRE pour interactivité

import { AppLayout } from '@/components/layouts/app-layout'
import { useAgents } from '@/services/agents/agents.hooks'

export default function AgentsPage() {
  const { data: agents, isLoading } = useAgents()

  if (isLoading) return <div>Chargement...</div>

  return (
    <AppLayout>
      {/* Contenu de la page */}
    </AppLayout>
  )
}
```

**Conventions** :
- Directive `'use client'` en première ligne (interactivité React)
- Hooks React Query pour data fetching
- Wrapped dans `AppLayout` ou `SidebarInset` pour layout cohérent
- Gestion des états loading/error

### Modals et Dialogs

**Pattern recommandé** :
```typescript
// Parent component
const [isOpen, setIsOpen] = useState(false)

<AgentModal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  onSave={(agent) => {
    // Handle save
    setIsOpen(false)
  }}
/>
```

**Composants existants** :
- `AgentModal` : Création/édition d'agents
- `TeamModal` : Création/édition de teams
- `ConfirmDialog` : Confirmation d'actions destructives

**Caractéristiques** :
- State contrôlé par le parent (`isOpen`, `setIsOpen`)
- Callbacks pour actions (`onClose`, `onSave`, `onDelete`)
- Validation avec Zod avant soumission
- Gestion erreurs avec toasts

### Forms

**Stack** : React Hook Form + Zod
```typescript
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const schema = z.object({
  name: z.string().min(1, 'Nom requis'),
  email: z.string().email('Email invalide'),
})

function MyForm() {
  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: { name: '', email: '' },
  })

  const onSubmit = form.handleSubmit(async (data) => {
    try {
      await createAgent.mutateAsync(data)
    } catch (error) {
      toast.error('Erreur')
    }
  })

  return (
    <form onSubmit={onSubmit}>
      <Input {...form.register('name')} />
      {form.formState.errors.name && (
        <p>{form.formState.errors.name.message}</p>
      )}
      <Button type="submit" disabled={form.formState.isSubmitting}>
        {form.formState.isSubmitting ? 'Envoi...' : 'Envoyer'}
      </Button>
    </form>
  )
}
```

**Bonnes pratiques** :
- Validation côté client avec Zod schema
- États de chargement (`isSubmitting`)
- Affichage des erreurs inline
- Désactivation du bouton pendant soumission
- Toast de succès/erreur

### SSR Safety (Next.js)

**Problèmes d'hydration** :
```typescript
// ❌ MAUVAIS - Cause hydration mismatch
function Component() {
  const theme = localStorage.getItem('theme')
  return <div>{theme}</div>
}

// ✅ BON - Attendre le montage client
function Component() {
  const [theme, setTheme] = useState<string | null>(null)

  useEffect(() => {
    setTheme(localStorage.getItem('theme'))
  }, [])

  if (theme === null) return null  // Ou skeleton

  return <div>{theme}</div>
}
```

**Checks recommandés** :
- `typeof window !== 'undefined'` pour API browser
- `useEffect` pour accès localStorage/sessionStorage
- `'use client'` pour composants interactifs
- Skeleton ou null pendant SSR

### Organisation des imports

**Ordre recommandé** :
```typescript
// 1. React et Next.js
import { useState } from 'react'
import { useRouter } from 'next/navigation'

// 2. Librairies externes
import { toast } from 'sonner'

// 3. Services et hooks
import { useAgents } from '@/services/agents/agents.hooks'

// 4. Composants
import { Button } from '@/components/ui/button'
import { AppLayout } from '@/components/layouts/app-layout'

// 5. Types
import type { Agent } from '@/services/agents/agents.types'
```

---

## 7. Points clés de sécurité

### Protection des données

- **Tokens** : Stockés en httpOnly cookies (inaccessibles en JavaScript)
- **Credentials** : Jamais en localStorage/sessionStorage
- **API calls** : Toujours via apiClient (withCredentials: true)
- **Logout** : Clear complet du cache React Query + cookies

### Protection des routes

- **Middleware** : Vérifie auth avant chaque route protégée
- **Redirections** : Automatiques vers /login si non authentifié
- **Token refresh** : Transparent et automatique (interceptor)

### Validation

- **Input** : Validation Zod côté client + backend
- **XSS** : Sanitization automatique avec React (dangerouslySetInnerHTML évité)
- **CSRF** : Protection via SameSite=Strict cookies

### Bonnes pratiques

- Pas de données sensibles dans l'URL ou query params
- Timeout API configurable (30s par défaut)
- Gestion erreurs centralisée (interceptors)
- Logs de sécurité en production (auth attempts, refresh failures)