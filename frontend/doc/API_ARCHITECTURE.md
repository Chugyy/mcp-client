# Architecture API - Documentation

Cette documentation explique l'architecture API mise en place pour le frontend, basée sur **React Query** et **Axios**, permettant une gestion scalable et maintenable des appels backend.

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Structure des fichiers](#structure-des-fichiers)
3. [Fichiers centraux](#fichiers-centraux)
4. [Structure d'un service](#structure-dun-service)
5. [Comment ajouter un nouveau service](#comment-ajouter-un-nouveau-service)
6. [Utilisation dans les composants](#utilisation-dans-les-composants)
7. [Bonnes pratiques](#bonnes-pratiques)

---

## 🎯 Vue d'ensemble

L'architecture repose sur 3 piliers :

1. **Client central** (`lib/api-client.ts`) : Configuration Axios + React Query + Auth
2. **Services par domaine** (`services/*/`) : Organisation modulaire des appels API
3. **Hooks React Query** : Gestion automatique du cache, loading, errors

### Avantages

✅ **Scalable** : Ajouter un nouveau domaine = dupliquer le pattern
✅ **Type-safe** : TypeScript end-to-end
✅ **Cache intelligent** : React Query gère le cache automatiquement
✅ **Optimistic updates** : UX fluide avec mises à jour optimistes
✅ **Centralisé** : Auth et config HTTP au même endroit
✅ **DX** : React Query DevTools pour debugging

---

## 📁 Structure des fichiers

```
src/
├── lib/
│   └── api-client.ts           # Client HTTP + React Query config + Auth
│
├── types/
│   └── api.types.ts            # Types génériques (ApiResponse, ApiError, etc.)
│
├── services/                    # Services organisés par domaine
│   ├── mcp/                    # Exemple : Serveurs MCP
│   │   ├── mcp.types.ts        # Types spécifiques MCP
│   │   ├── mcp.service.ts      # Fonctions API + Query keys
│   │   └── mcp.hooks.ts        # Hooks React Query
│   │
│   ├── agents/                 # Exemple : Agents
│   │   ├── agents.types.ts
│   │   ├── agents.service.ts
│   │   └── agents.hooks.ts
│   │
│   └── chats/                  # Exemple : Chats
│       ├── chats.types.ts
│       ├── chats.service.ts
│       └── chats.hooks.ts
│
└── app/
    └── layout.tsx              # QueryClientProvider configuré
```

---

## 🔧 Fichiers centraux

### 1. `.env.local` - Configuration

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 2. `lib/api-client.ts` - Client unique

Ce fichier contient **tout** ce qui est partagé :

- **Client Axios** configuré avec baseURL
- **Intercepteurs** pour ajouter le token automatiquement
- **QueryClient React Query** avec options par défaut
- **Helpers auth** (getToken, setToken, clearToken)

```typescript
import axios from 'axios'
import { QueryClient } from '@tanstack/react-query'

// Instance Axios
export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Intercepteur auth
apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// QueryClient
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 min
    },
  },
})

// Auth helpers
export function getToken() { ... }
export function setToken(token: string) { ... }
export function clearToken() { ... }
```

### 3. `app/layout.tsx` - Provider

Le `QueryClientProvider` est configuré au niveau root :

```tsx
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { queryClient } from '@/lib/api-client'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <QueryClientProvider client={queryClient}>
          {/* Autres providers */}
          {children}
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </body>
    </html>
  )
}
```

---

## 📦 Structure d'un service

Chaque service est organisé en **3 fichiers** dans un dossier dédié.

### Exemple : Service MCP (`services/mcp/`)

#### 1. `mcp.types.ts` - Types TypeScript

```typescript
export interface MCPServer {
  id: string
  name: string
  description?: string
  url: string
  authType: 'api-key' | 'oauth'
  enabled: boolean
}

export interface CreateMCPServerDTO {
  name: string
  url: string
  authType: 'api-key' | 'oauth'
}

export interface UpdateMCPServerDTO {
  name?: string
  url?: string
  enabled?: boolean
}
```

#### 2. `mcp.service.ts` - Fonctions API + Query keys

```typescript
import { apiClient } from '@/lib/api-client'
import type { MCPServer, CreateMCPServerDTO } from './mcp.types'

// Query keys pour React Query
export const mcpKeys = {
  all: ['mcp'] as const,
  lists: () => [...mcpKeys.all, 'list'] as const,
  detail: (id: string) => [...mcpKeys.all, 'detail', id] as const,
}

// Fonctions API
export const mcpService = {
  async getAll(): Promise<MCPServer[]> {
    const { data } = await apiClient.get('/mcp/servers')
    return data
  },

  async create(dto: CreateMCPServerDTO): Promise<MCPServer> {
    const { data } = await apiClient.post('/mcp/servers', dto)
    return data
  },

  async update(id: string, dto: UpdateMCPServerDTO): Promise<MCPServer> {
    const { data } = await apiClient.patch(`/mcp/servers/${id}`, dto)
    return data
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/mcp/servers/${id}`)
  },
}
```

#### 3. `mcp.hooks.ts` - Hooks React Query

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { mcpService, mcpKeys } from './mcp.service'

// Hook pour GET
export function useMCPServers() {
  return useQuery({
    queryKey: mcpKeys.lists(),
    queryFn: mcpService.getAll,
  })
}

// Hook pour CREATE
export function useCreateMCPServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: mcpService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.all })
      toast.success('Serveur créé avec succès')
    },
    onError: () => {
      toast.error('Erreur lors de la création')
    },
  })
}

// Hook pour UPDATE avec optimistic update
export function useUpdateMCPServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }) => mcpService.update(id, data),
    onMutate: async ({ id, data }) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: mcpKeys.lists() })
      const previousData = queryClient.getQueryData(mcpKeys.lists())

      queryClient.setQueryData(mcpKeys.lists(), (old) =>
        old.map((item) => (item.id === id ? { ...item, ...data } : item))
      )

      return { previousData }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.all })
      toast.success('Serveur mis à jour')
    },
    onError: (_, __, context) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(mcpKeys.lists(), context.previousData)
      }
      toast.error('Erreur lors de la mise à jour')
    },
  })
}

// Hook pour DELETE
export function useDeleteMCPServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: mcpService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.all })
      toast.success('Serveur supprimé')
    },
  })
}
```

---

## ➕ Comment ajouter un nouveau service

Suivez ces étapes pour ajouter un nouveau domaine (ex: `agents`) :

### Étape 1 : Créer le dossier et les fichiers

```bash
mkdir -p src/services/agents
touch src/services/agents/agents.types.ts
touch src/services/agents/agents.service.ts
touch src/services/agents/agents.hooks.ts
```

### Étape 2 : Définir les types (`agents.types.ts`)

```typescript
export interface Agent {
  id: string
  name: string
  description?: string
  enabled: boolean
}

export interface CreateAgentDTO {
  name: string
  description?: string
}

export interface UpdateAgentDTO {
  name?: string
  description?: string
  enabled?: boolean
}
```

### Étape 3 : Créer le service (`agents.service.ts`)

```typescript
import { apiClient } from '@/lib/api-client'
import type { Agent, CreateAgentDTO, UpdateAgentDTO } from './agents.types'

// Query keys
export const agentKeys = {
  all: ['agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  detail: (id: string) => [...agentKeys.all, 'detail', id] as const,
}

// Service
export const agentService = {
  async getAll(): Promise<Agent[]> {
    const { data } = await apiClient.get('/agents')
    return data
  },

  async getById(id: string): Promise<Agent> {
    const { data } = await apiClient.get(`/agents/${id}`)
    return data
  },

  async create(dto: CreateAgentDTO): Promise<Agent> {
    const { data } = await apiClient.post('/agents', dto)
    return data
  },

  async update(id: string, dto: UpdateAgentDTO): Promise<Agent> {
    const { data } = await apiClient.patch(`/agents/${id}`, dto)
    return data
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/agents/${id}`)
  },
}
```

### Étape 4 : Créer les hooks (`agents.hooks.ts`)

```typescript
"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { agentService, agentKeys } from './agents.service'
import type { CreateAgentDTO, UpdateAgentDTO } from './agents.types'

export function useAgents() {
  return useQuery({
    queryKey: agentKeys.lists(),
    queryFn: agentService.getAll,
  })
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: agentKeys.detail(id),
    queryFn: () => agentService.getById(id),
    enabled: !!id,
  })
}

export function useCreateAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: CreateAgentDTO) => agentService.create(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
      toast.success('Agent créé avec succès')
    },
    onError: () => {
      toast.error('Erreur lors de la création')
    },
  })
}

export function useUpdateAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateAgentDTO }) =>
      agentService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
      toast.success('Agent mis à jour')
    },
  })
}

export function useDeleteAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => agentService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.all })
      toast.success('Agent supprimé')
    },
  })
}
```

### Étape 5 : Utiliser dans un composant

```tsx
import { useAgents, useCreateAgent, useDeleteAgent } from '@/services/agents/agents.hooks'

export default function AgentsPage() {
  const { data: agents, isLoading, error } = useAgents()
  const createAgent = useCreateAgent()
  const deleteAgent = useDeleteAgent()

  if (isLoading) return <div>Chargement...</div>
  if (error) return <div>Erreur : {error.message}</div>

  return (
    <div>
      <button onClick={() => createAgent.mutate({ name: 'Nouvel agent' })}>
        Créer un agent
      </button>

      {agents?.map((agent) => (
        <div key={agent.id}>
          <h3>{agent.name}</h3>
          <button onClick={() => deleteAgent.mutate(agent.id)}>Supprimer</button>
        </div>
      ))}
    </div>
  )
}
```

---

## 🎨 Utilisation dans les composants

### Exemple : Page MCP Tools

```tsx
"use client"

import { useMCPServers, useCreateMCPServer, useDeleteMCPServer } from '@/services/mcp/mcp.hooks'

export default function MCPToolsPage() {
  const { data: mcpServers, isLoading, error } = useMCPServers()
  const createMCP = useCreateMCPServer()
  const deleteMCP = useDeleteMCPServer()

  const handleCreate = () => {
    createMCP.mutate({
      name: 'Nouveau serveur',
      url: 'https://api.example.com',
      authType: 'api-key',
    })
  }

  if (isLoading) return <div>Chargement...</div>
  if (error) return <div>Erreur : {error.message}</div>

  return (
    <div>
      <button onClick={handleCreate} disabled={createMCP.isPending}>
        {createMCP.isPending ? 'Création...' : 'Créer un serveur MCP'}
      </button>

      {mcpServers?.map((mcp) => (
        <div key={mcp.id}>
          <h3>{mcp.name}</h3>
          <button onClick={() => deleteMCP.mutate(mcp.id)}>Supprimer</button>
        </div>
      ))}
    </div>
  )
}
```

### États disponibles

React Query fournit automatiquement :

- `data` : Les données retournées par l'API
- `isLoading` : Chargement initial
- `isFetching` : Rechargement en arrière-plan
- `error` : Erreur éventuelle
- `refetch()` : Fonction pour forcer un refetch

Pour les mutations :

- `mutate()` : Fonction pour déclencher la mutation
- `isPending` : Mutation en cours
- `isSuccess` : Mutation réussie
- `isError` : Mutation échouée

---

## ✅ Bonnes pratiques

### 1. Query Keys

Toujours définir les query keys dans le service :

```typescript
export const domainKeys = {
  all: ['domain'] as const,
  lists: () => [...domainKeys.all, 'list'] as const,
  detail: (id: string) => [...domainKeys.all, 'detail', id] as const,
  filtered: (filters: Filters) => [...domainKeys.all, 'list', filters] as const,
}
```

### 2. Optimistic Updates

Pour une UX fluide, utilisez les optimistic updates sur les mutations fréquentes (toggle, update) :

```typescript
onMutate: async (newData) => {
  await queryClient.cancelQueries({ queryKey: keys.lists() })
  const previousData = queryClient.getQueryData(keys.lists())

  queryClient.setQueryData(keys.lists(), (old) => updateLogic(old, newData))

  return { previousData }
},
onError: (_, __, context) => {
  // Rollback
  queryClient.setQueryData(keys.lists(), context.previousData)
},
```

### 3. Gestion des erreurs

Toujours afficher un message clair à l'utilisateur :

```typescript
onError: (error: any) => {
  const message = error.response?.data?.message || 'Une erreur est survenue'
  toast.error(message)
},
```

### 4. Types TypeScript

Toujours typer les réponses API et les DTOs :

```typescript
async getAll(): Promise<Item[]> { ... }
async create(dto: CreateItemDTO): Promise<Item> { ... }
```

### 5. Loading states

Gérer les états de chargement dans l'UI :

```tsx
if (isLoading) return <Skeleton />
if (error) return <ErrorMessage error={error} />
if (!data) return <EmptyState />
```

### 6. Invalidation du cache

Invalider le cache après les mutations pour garantir la cohérence :

```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: keys.all })
}
```

### 7. React Query DevTools

Utilisez les DevTools en développement pour debugger :

```tsx
<ReactQueryDevtools initialIsOpen={false} />
```

---

## 🚀 Résumé

Pour ajouter un nouveau domaine :

1. **Créer** le dossier `services/domain/`
2. **Définir** les types dans `domain.types.ts`
3. **Créer** le service dans `domain.service.ts` (fonctions API + query keys)
4. **Créer** les hooks dans `domain.hooks.ts` (useQuery + useMutation)
5. **Utiliser** les hooks dans vos composants

Cette architecture vous permet de gérer **100+ endpoints** de manière scalable et maintenable.

---

## 📚 Ressources

- [React Query Documentation](https://tanstack.com/query/latest)
- [Axios Documentation](https://axios-http.com/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
