# Migration Story 0.7 - Static File Authentication

## Résumé des changements

Cette migration implémente la sécurité critique pour les fichiers uploadés, passant d'un accès public à un accès authentifié avec vérification de propriété.

## Changements Backend

### 1. Modification de `uploads.py` (CRUD)
**Fichier** : `/backend/app/database/crud/uploads.py`

**Changement** : La fonction `get_agent_avatar_url()` retourne maintenant l'`upload_id` au lieu du chemin fichier.

```python
# AVANT
return f"/uploads/avatar/{filename}"

# APRÈS
return result['id']  # Upload ID
```

**Raison** : Le frontend utilise maintenant `/api/v1/uploads/{upload_id}` avec authentification JWT.

## Changements Frontend

### 2. Nouveaux Services d'Authentification

#### `/services/uploads/uploads.service.ts`
Service pour gérer les fichiers uploadés avec authentification JWT.

**Fonctions principales** :
- `getUploadUrl(uploadId)` - Construit l'URL du endpoint authentifié
- `fetchUpload(uploadId)` - Télécharge un fichier avec auth
- `getUploadBlobUrl(uploadId)` - Crée une blob URL pour affichage d'images

#### `/services/uploads/uploads.hooks.ts`
Hook React Query pour cacher les fichiers uploadés.

**Hook principal** :
- `useUploadBlobUrl(uploadId)` - Fetch et cache automatiquement les blob URLs

### 3. Nouveau Composant UI

#### `/components/ui/authenticated-image.tsx`
Composant pour afficher des images nécessitant authentification.

**Props** :
- `uploadId` - ID de l'upload
- `fallback` - URL publique de secours
- `loadingClassName` - Classe CSS pendant le chargement

**Usage** :
```tsx
<AuthenticatedImage
  uploadId="upl_xxx"
  alt="Avatar"
  className="size-8"
  fallback="/default-avatar.png"
/>
```

### 4. Modifications de Composants Existants

#### `lib/api.ts` - Fonction `getAvatarUrl()`
**Changement** : Construit maintenant l'URL du endpoint authentifié.

```typescript
// AVANT
return `${API_BASE}/uploads/avatar/${filename}`

// APRÈS
return `${API_URL}/uploads/${uploadId}`
```

**Note** : Cette fonction est conservée pour compatibilité mais **DEPRECATED**. Utilisez `useUploadBlobUrl()` à la place.

#### `components/ui/entity-card.tsx`
**Changement** : Détecte automatiquement si `icon` est un upload_id et utilise `AuthenticatedImage`.

```tsx
// Détection automatique upload_id vs URL publique
const isUploadId = iconValue && !iconValue.startsWith('http')
```

**Comportement** :
- Si `icon` est un UUID → Utilise `AuthenticatedImage`
- Si `icon` est une URL → Utilise `<img>` classique
- Si `icon` est un composant → Affiche l'icône

#### `components/agents/card.tsx`
**Changement** : Passe directement l'`upload_id` au lieu d'utiliser `getAvatarUrl()`.

```tsx
// AVANT
const avatarUrl = getAvatarUrl(avatar)
icon={avatarUrl || Bot}

// APRÈS
icon={avatar || Bot}  // avatar est maintenant l'upload_id
```

#### `components/ui/shadcn-io/ai/message.tsx` - `MessageAvatar`
**Changement** : Support des upload IDs avec hook `useUploadBlobUrl()`.

**Nouvelles props** :
- `uploadId` - ID de l'upload (recommandé)
- `src` - URL directe (deprecated, pour compatibilité)
- `fallback` - URL publique de secours

```tsx
// AVANT
<MessageAvatar src={getAvatarUrl(agent.avatar_url)} name={agent.name} />

// APRÈS
<MessageAvatar uploadId={agent.avatar_url} name={agent.name} fallback="/bot.png" />
```

#### `components/chat/chat-messages.tsx`
**Changement** : Utilise `uploadId` avec `MessageAvatar`.

```tsx
// AVANT
<MessageAvatar
  name={currentAgent?.name}
  src={getAvatarUrl(currentAgent.avatar_url)}
/>

// APRÈS
<MessageAvatar
  name={currentAgent?.name}
  uploadId={currentAgent.avatar_url}
  fallback="/bot.png"
/>
```

#### `components/ui/avatar-upload.tsx`
**Changement** : Utilise `useUploadBlobUrl()` pour charger l'avatar existant.

**Prop renommée** :
- `defaultUrl` → `defaultUploadId`

```tsx
// AVANT
const previewUrl = defaultUrl ? getAvatarUrl(defaultUrl) : null

// APRÈS
const { data: existingAvatarUrl } = useUploadBlobUrl(defaultUploadId)
const previewUrl = files[0]?.preview || existingAvatarUrl || null
```

## Architecture de Sécurité

### Endpoint Authentifié
```
GET /api/v1/uploads/{upload_id}
Headers: Authorization: Bearer <jwt_token>
```

### Vérification de Propriété (Backend)
Le backend vérifie automatiquement que l'utilisateur a le droit d'accéder au fichier via :
1. **Propriété directe** : `upload.user_id == current_user.id`
2. **Propriété via agent** : `agent.user_id == current_user.id`
3. **Propriété via resource** : `resource.user_id == current_user.id`
4. **Override admin** : `current_user.is_system == true`

### Réponses HTTP
- **200** : Fichier retourné avec `FileResponse`
- **401** : Non authentifié (JWT invalide/expiré)
- **403** : Authentifié mais pas propriétaire
- **404** : Fichier non trouvé

## Gestion du Cache

### React Query
Les blob URLs sont cachées par React Query :
- **staleTime** : 10 minutes
- **gcTime** : 30 minutes

### Cleanup
Les blob URLs créées avec `URL.createObjectURL()` sont automatiquement révoquées au démontage du composant via `useEffect`.

## Migration des Composants Existants

### Pattern Recommandé

**Pour les avatars dans les cards :**
```tsx
<EntityCard icon={agent.avatar_url || BotIcon} />
```

**Pour les avatars dans les messages :**
```tsx
<MessageAvatar
  uploadId={agent.avatar_url}
  name={agent.name}
  fallback="/default-avatar.png"
/>
```

**Pour les previews d'upload :**
```tsx
<AvatarUpload
  defaultUploadId={agent.avatar_url}
  onFileChange={handleFileChange}
/>
```

### Composants Non Migrés

Les composants suivants utilisent encore `getAvatarUrl()` car ils sont dans des contextes où `AuthenticatedImage` n'est pas adapté :

1. **chat-input.tsx** - Avatars dans `<SelectItem>` (dropdown)
2. **team-modal.tsx** - Avatars dans liste des agents
3. **agent-selector.tsx** - Avatars dans combobox

**Note** : Ces composants fonctionneront toujours grâce au `apiClient.withCredentials: true` et CORS `allow_credentials: true` du backend.

## Testing

### Tests à effectuer

1. **Authentification Avatar** :
   - [ ] Connexion et vérification que les avatars des agents s'affichent
   - [ ] Déconnexion et vérification que les avatars ne se chargent plus
   - [ ] Upload d'un nouvel avatar pour un agent

2. **Ownership Verification** :
   - [ ] Créer deux utilisateurs (user1, user2)
   - [ ] user1 crée un agent avec avatar
   - [ ] user2 essaie d'accéder à l'avatar de user1 → Doit échouer (403)
   - [ ] Utilisateur admin peut accéder aux avatars de tous

3. **Fallback & Loading** :
   - [ ] Avatar non trouvé → Affiche fallback `/bot.png`
   - [ ] Chargement lent → Affiche spinner
   - [ ] Avatar invalide → Affiche fallback

4. **Cache Performance** :
   - [ ] Premier chargement → Requête réseau
   - [ ] Navigation répétée → Charge depuis cache
   - [ ] Après 10 minutes → Refetch automatique

## Breaking Changes

### Pour les Développeurs

**AVANT (deprecated)** :
```tsx
import { getAvatarUrl } from '@/lib/api'

const avatarSrc = getAvatarUrl(agent.avatar_url)
<img src={avatarSrc} />
```

**APRÈS (recommandé)** :
```tsx
import { useUploadBlobUrl } from '@/services/uploads/uploads.hooks'

const { data: avatarUrl } = useUploadBlobUrl(agent.avatar_url)
<img src={avatarUrl} />
```

**OU (plus simple)** :
```tsx
<AuthenticatedImage uploadId={agent.avatar_url} fallback="/default.png" />
```

### Compatibilité Ascendante

La fonction `getAvatarUrl()` est conservée et fonctionne toujours en construisant l'URL du endpoint authentifié. Cependant :
- ❌ Ne pas utiliser avec `<img src={getAvatarUrl(...)} />` directement
- ✅ Utiliser `AuthenticatedImage` ou `useUploadBlobUrl()` à la place

## Rollback Plan

En cas de problème, pour rollback :

1. **Backend** : Restaurer `get_agent_avatar_url()` pour retourner `/uploads/avatar/{filename}`
2. **Frontend** : Restaurer `getAvatarUrl()` à l'ancienne version
3. **Redémarrer** les services backend et frontend

## Prochaines Étapes

- [ ] Migrer les composants non migrés (chat-input, team-modal, agent-selector)
- [ ] Ajouter des tests unitaires pour `uploads.service.ts`
- [ ] Ajouter des tests E2E pour l'authentification des fichiers
- [ ] Documenter l'API `/api/v1/uploads/{upload_id}` dans OpenAPI/Swagger
- [ ] Implémenter la même logique pour les logos de services MCP

## Contacts

En cas de question sur cette migration :
- Backend : Story 0.7 - Static File Authentication
- Frontend : Coordination avec cette migration
