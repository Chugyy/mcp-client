# Plan de tests MCP - Frontend

## Objectif
Vérifier que l'intégration frontend du service MCP fonctionne correctement avec l'API backend.

---

## Prérequis

- Backend démarré sur `http://localhost:8000`
- Token JWT valide stocké dans localStorage
- Compte utilisateur authentifié

---

## Tests UI essentiels

### Test 1 : Affichage liste serveurs MCP

**Étapes** :
1. Ouvrir la page `/mcp-tools`
2. Vérifier que la liste des serveurs s'affiche
3. Vérifier les badges de status sur chaque carte :
   - Badge "Active" si `status='active'`
   - Badge "Pending OAuth" si `status='pending_authorization'`
   - Badge "Failed" si `status='failed'`
   - Badge "Needs Sync" si `stale=true` (last_health_check > 24h)

**Résultat attendu** :
- Liste des serveurs affichée correctement
- Badges de status visibles et corrects
- Pas d'erreur console

---

### Test 2 : Création serveur MCP (auth_type='api-key')

**Étapes** :
1. Cliquer sur le bouton "+" pour ouvrir le modal
2. Remplir le formulaire :
   - `name` : "Test API Key Server"
   - `url` : "https://api.example.com"
   - `auth_type` : Sélectionner "API Key"
   - `service_id` : "test-service"
   - `api_key_value` : "sk-test-123456"
   - `enabled` : true
3. Cliquer "Créer"

**Résultat attendu** :
- Toast success "Serveur MCP créé avec succès"
- Le nouveau serveur apparaît dans la liste
- Requête POST `/api/v1/servers` envoyée avec le bon payload
- Modal se ferme automatiquement

---

### Test 3 : Création serveur MCP (auth_type='oauth')

**Étapes** :
1. Cliquer sur le bouton "+"
2. Remplir le formulaire :
   - `name` : "Test OAuth Server"
   - `url` : "https://oauth.example.com"
   - `auth_type` : Sélectionner "OAuth"
   - `enabled` : true
3. Cliquer "Créer"

**Résultat attendu** :
- Toast success "Serveur MCP créé avec succès"
- **Si backend retourne `status='pending_authorization'`** :
  - Une popup s'ouvre avec l'URL OAuth contenue dans `status_message`
  - Le serveur apparaît avec badge "Pending OAuth"
- **Si backend retourne `status='active'`** :
  - Le serveur apparaît avec badge "Active"

---

### Test 4 : Création serveur MCP (auth_type='none')

**Étapes** :
1. Cliquer sur le bouton "+"
2. Remplir le formulaire :
   - `name` : "Test No Auth Server"
   - `url` : "https://public.example.com"
   - `auth_type` : Sélectionner "None"
   - `enabled` : true
3. Cliquer "Créer"

**Résultat attendu** :
- Aucun champ `service_id` ou `api_key_value` visible dans le formulaire
- Toast success
- Serveur créé avec `status='active'` ou `status='pending'`

---

### Test 5 : Toggle enable/disable serveur

**Étapes** :
1. Localiser un serveur dans la liste
2. Cliquer sur le toggle (switch) pour désactiver
3. Observer l'UI
4. Cliquer à nouveau pour réactiver

**Résultat attendu** :
- **Optimistic update** : Le toggle change immédiatement (avant réponse backend)
- Toast "Serveur MCP désactivé" puis "Serveur MCP activé"
- Requête PATCH `/api/v1/servers/{id}` avec `{ enabled: false }` puis `{ enabled: true }`
- En cas d'erreur backend → UI revient à l'état précédent (rollback)

---

### Test 6 : Suppression serveur

**Étapes** :
1. Cliquer sur le bouton "Supprimer" d'un serveur
2. Confirmer dans le dialog de confirmation
3. Observer l'UI

**Résultat attendu** :
- Dialog de confirmation s'affiche avec message "Êtes-vous sûr de vouloir supprimer ce serveur MCP ?"
- **Optimistic update** : Le serveur disparaît immédiatement de la liste
- Toast "Serveur supprimé"
- Requête DELETE `/api/v1/servers/{id}` envoyée
- En cas d'erreur → serveur réapparaît (rollback)

---

### Test 7 : Synchronisation serveur

**Étapes** :
1. Localiser un serveur avec badge "Needs Sync" ou n'importe quel serveur
2. Cliquer sur le bouton "Sync" (icône refresh)
3. Observer le comportement

**Résultat attendu** :
- **Cas 1 : Succès (200)** :
  - Toast "Serveur synchronisé"
  - `last_health_check` mis à jour
  - Badge "Needs Sync" disparaît si présent

- **Cas 2 : Erreur 401 (OAuth expiré)** :
  - Popup OAuth s'ouvre avec l'URL retournée dans le message d'erreur
  - Toast "Veuillez autoriser l'accès OAuth"

- Requête POST `/api/v1/servers/{id}/sync` envoyée

---

### Test 8 : Recherche/Filtrage serveurs

**Étapes** :
1. Taper un nom de serveur dans le champ de recherche
2. Observer la liste filtrée
3. Effacer la recherche

**Résultat attendu** :
- La liste se filtre en temps réel
- Seuls les serveurs dont le nom contient la chaîne recherchée s'affichent
- Message "Aucun serveur MCP trouvé" si aucun résultat

---

### Test 9 : Modification serveur existant

**Étapes** :
1. Cliquer sur le bouton "Éditer" d'un serveur
2. Modifier le champ `name` : "Nouveau nom"
3. Modifier `enabled` : inverser la valeur
4. Cliquer "Enregistrer"

**Résultat attendu** :
- Modal s'ouvre avec les données existantes pré-remplies
- **Optimistic update** : Changements visibles immédiatement
- Toast "Serveur mis à jour"
- Requête PATCH `/api/v1/servers/{id}` avec `{ name: "Nouveau nom", enabled: ... }`
- En cas d'erreur → rollback

---

### Test 10 : Badge "Needs Sync" (stale)

**Étapes** :
1. Créer un serveur
2. Attendre 24h OU modifier manuellement en base `last_health_check` à une date > 24h
3. Rafraîchir la page `/mcp-tools`

**Résultat attendu** :
- Le serveur affiche le badge "Needs Sync"
- Le champ `stale=true` est retourné par `GET /api/v1/servers?with_tools=true`

---

## Tests techniques (DevTools)

### Vérifications Network (onglet Réseau)

**Créer serveur** :
- Méthode : `POST /api/v1/servers`
- Payload contient : `name`, `url`, `auth_type`, `service_id` (si api-key), `api_key_value` (si api-key)
- Réponse 201 : Objet `MCPServer` complet

**Lister serveurs** :
- Méthode : `GET /api/v1/servers?with_tools=true`
- Réponse 200 : Array de `MCPServerWithTools[]`

**Synchroniser** :
- Méthode : `POST /api/v1/servers/{id}/sync`
- Réponse 200 ou 401

**Toggle** :
- Méthode : `PATCH /api/v1/servers/{id}`
- Payload : `{ enabled: boolean }`

**Supprimer** :
- Méthode : `DELETE /api/v1/servers/{id}`
- Réponse 204

---

## Erreurs à vérifier

### Erreur 401 (Non authentifié)
- Supprimer le token du localStorage
- Rafraîchir `/mcp-tools`
- **Attendu** : Redirection vers `/login`

### Erreur 404 (Serveur introuvable)
- Essayer de modifier un serveur avec un ID inexistant
- **Attendu** : Toast "Erreur lors de la mise à jour"

### Erreur réseau (Backend offline)
- Arrêter le backend
- Essayer de créer un serveur
- **Attendu** : Toast d'erreur explicite

---

## Checklist finale

- [ ] Tous les serveurs s'affichent correctement
- [ ] Création serveur (api-key, oauth, none) fonctionne
- [ ] Modification serveur fonctionne avec optimistic update
- [ ] Suppression serveur fonctionne avec optimistic update
- [ ] Toggle enable/disable fonctionne avec optimistic update
- [ ] Synchronisation fonctionne + gestion erreur 401 OAuth
- [ ] Badges status ("Active", "Pending OAuth", "Failed", "Needs Sync") s'affichent
- [ ] Recherche/filtrage fonctionne
- [ ] Aucune erreur console
- [ ] Toasts success/error s'affichent correctement
- [ ] Popup OAuth s'ouvre quand `status='pending_authorization'`
- [ ] Rollback optimistic fonctionne en cas d'erreur backend

---

**Date de création** : 2025-11-30
**Version API Backend** : 1-mcp.md
