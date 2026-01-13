# Plan de Test - Module Ressources

## 📋 Vue d'ensemble

Ce document décrit le plan de test complet pour le module de gestion des ressources RAG.

**Date de création** : 2025-12-01
**Version** : 1.0.0
**Périmètre** : Service Resources (types, service, hooks, UI)

---

## 🎯 Objectifs

- Valider l'intégration complète de l'API Resources avec le frontend
- Tester toutes les opérations CRUD (Create, Read, Update, Delete)
- Vérifier la gestion des uploads de fichiers
- Valider le processus d'ingestion RAG
- Tester la gestion d'erreurs et les cas limites

---

## 🧪 Environnement de test

### Prérequis

- Backend FastAPI en cours d'exécution (http://localhost:8000)
- Base de données configurée avec les tables `resources` et `uploads`
- Frontend Next.js en dev mode (http://localhost:3000)
- Utilisateur authentifié dans l'application

### Données de test

**Fichiers de test à préparer** :
- `test-document.pdf` (< 10MB)
- `test-presentation.pptx` (< 5MB)
- `test-spreadsheet.xlsx` (< 5MB)
- `test-large-file.pdf` (> 10MB, pour test de limite)
- `test-invalid-type.exe` (type MIME non autorisé)

---

## 📝 Plan de Test Détaillé

### Phase 1 : Tests du Service Base

#### Test 1.1 : Création du service
**Objectif** : Vérifier que les fichiers du service sont correctement créés

**Étapes** :
1. Vérifier l'existence de `src/services/resources/resources.types.ts`
2. Vérifier l'existence de `src/services/resources/resources.service.ts`
3. Vérifier l'existence de `src/services/resources/resources.hooks.ts`
4. Compiler le projet TypeScript (`npm run build` ou `npx tsc --noEmit`)

**Résultat attendu** :
- ✅ Tous les fichiers existent
- ✅ Aucune erreur de compilation TypeScript
- ✅ Les imports sont correctement résolus

---

#### Test 1.2 : Validation des types TypeScript
**Objectif** : Vérifier la cohérence des types avec le backend

**Étapes** :
1. Ouvrir `resources.types.ts`
2. Vérifier que l'interface `Resource` correspond à `ResourceResponse` du backend
3. Vérifier que `Upload` correspond à `UploadResponse` du backend
4. Vérifier les DTOs (`CreateResourceDTO`, `UpdateResourceDTO`)

**Résultat attendu** :
- ✅ Tous les champs correspondent au backend
- ✅ Les types sont correctement typés (string, number, boolean, null)
- ✅ Les champs optionnels sont marqués avec `?` ou `| null`

---

#### Test 1.3 : Query keys React Query
**Objectif** : Vérifier la structure des query keys

**Étapes** :
1. Ouvrir `resources.service.ts`
2. Vérifier la structure de `resourceKeys`

**Résultat attendu** :
```typescript
resourceKeys = {
  all: ['resources'],
  lists: () => ['resources', 'list'],
  list: (filters) => ['resources', 'list', filters],
  detail: (id) => ['resources', 'detail', id],
  uploads: (resourceId) => ['resources', resourceId, 'uploads']
}
```

---

### Phase 2 : Tests CRUD (Interface UI)

#### Test 2.1 : Lister les ressources (READ)
**Objectif** : Tester l'affichage de la liste des ressources

**Étapes** :
1. Ouvrir la page `/ressources`
2. Vérifier l'affichage de la liste (vide ou avec données)
3. Observer les logs réseau (DevTools → Network)

**Résultat attendu** :
- ✅ Requête `GET /api/v1/resources` effectuée
- ✅ Status 200 OK
- ✅ Les ressources s'affichent dans la grille
- ✅ Les cartes affichent : nom, description, status, chunk_count
- ✅ Si aucune ressource : message "Aucune ressource disponible"

**États de chargement** :
- ✅ Spinner ou skeleton pendant le chargement
- ✅ Données affichées après chargement

---

#### Test 2.2 : Créer une ressource (CREATE)
**Objectif** : Tester la création d'une nouvelle ressource

**Étapes** :
1. Cliquer sur le bouton "+" (Créer)
2. Remplir le formulaire modal :
   - Nom : "Test Resource 1"
   - Description : "Ressource de test pour validation"
   - Enabled : true
   - Auto-ingest : false (pour l'instant)
3. Cliquer sur "Sauvegarder"
4. Observer les logs réseau

**Résultat attendu** :
- ✅ Modal s'ouvre correctement
- ✅ Requête `POST /api/v1/resources` effectuée
- ✅ Status 201 Created
- ✅ Toast de succès "Ressource créée avec succès"
- ✅ Modal se ferme
- ✅ La nouvelle ressource apparaît dans la liste
- ✅ Le cache React Query est invalidé (liste se recharge)

**Données de la requête** :
```json
{
  "name": "Test Resource 1",
  "description": "Ressource de test pour validation",
  "enabled": true,
  "embedding_model": "text-embedding-3-large",
  "embedding_dim": 3072
}
```

---

#### Test 2.3 : Modifier une ressource (UPDATE)
**Objectif** : Tester la mise à jour d'une ressource existante

**Étapes** :
1. Cliquer sur une carte de ressource pour éditer
2. Modifier le nom : "Test Resource 1 - Updated"
3. Modifier la description
4. Cliquer sur "Sauvegarder"

**Résultat attendu** :
- ✅ Modal s'ouvre avec les données pré-remplies
- ✅ Requête `PATCH /api/v1/resources/{id}` effectuée
- ✅ Status 200 OK
- ✅ Toast de succès "Ressource mise à jour"
- ✅ Les modifications apparaissent immédiatement dans la liste
- ✅ Le cache React Query est invalidé

---

#### Test 2.4 : Activer/Désactiver une ressource (TOGGLE)
**Objectif** : Tester le toggle enabled/disabled

**Étapes** :
1. Localiser le switch "Enabled" sur une carte
2. Cliquer pour désactiver
3. Observer le changement visuel
4. Cliquer pour réactiver

**Résultat attendu** :
- ✅ Requête `PATCH /api/v1/resources/{id}` avec `{ enabled: false }`
- ✅ Status 200 OK
- ✅ Toast "Ressource désactivée" puis "Ressource activée"
- ✅ L'état visuel change (badge, opacité, etc.)
- ✅ Le cache React Query est mis à jour

---

#### Test 2.5 : Supprimer une ressource (DELETE)
**Objectif** : Tester la suppression d'une ressource

**Étapes** :
1. Cliquer sur le bouton "Supprimer" d'une carte
2. Confirmer dans la boîte de dialogue
3. Observer les logs réseau

**Résultat attendu** :
- ✅ Dialog de confirmation s'affiche
- ✅ Requête `DELETE /api/v1/resources/{id}` effectuée
- ✅ Status 204 No Content
- ✅ Toast de succès "Ressource supprimée"
- ✅ La ressource disparaît de la liste
- ✅ Le cache React Query est invalidé

**Test d'annulation** :
- Cliquer sur "Annuler" dans le dialog
- ✅ Aucune requête effectuée
- ✅ La ressource reste dans la liste

---

### Phase 3 : Tests Upload de Fichiers

#### Test 3.1 : Upload de fichiers valides
**Objectif** : Tester l'upload de fichiers autorisés

**Étapes** :
1. Créer ou éditer une ressource
2. Ajouter des fichiers via le champ de sélection :
   - `test-document.pdf`
   - `test-presentation.pptx`
3. Sauvegarder la ressource

**Résultat attendu** :
- ✅ Les fichiers sont listés dans le modal avant sauvegarde
- ✅ Requête `POST /api/v1/uploads` effectuée pour chaque fichier
- ✅ FormData contient : `file`, `upload_type="resource"`, `resource_id`
- ✅ Status 201 Created pour chaque upload
- ✅ Les uploads apparaissent dans la liste des fichiers de la ressource
- ✅ Les métadonnées sont correctes (filename, size, mime_type)

---

#### Test 3.2 : Upload de fichiers invalides
**Objectif** : Tester le rejet des fichiers non autorisés

**Étapes** :
1. Tenter d'uploader `test-invalid-type.exe`

**Résultat attendu** :
- ✅ Erreur côté backend (Status 400)
- ✅ Toast d'erreur "Type de fichier non autorisé"
- ✅ Le fichier n'est pas uploadé

---

#### Test 3.3 : Upload de fichier trop volumineux
**Objectif** : Tester la limite de taille

**Étapes** :
1. Tenter d'uploader `test-large-file.pdf` (> 10MB)

**Résultat attendu** :
- ✅ Erreur côté backend (Status 413)
- ✅ Toast d'erreur "Fichier trop volumineux. Taille max : 10MB"

---

#### Test 3.4 : Supprimer un upload
**Objectif** : Tester la suppression d'un fichier uploadé

**Étapes** :
1. Ouvrir une ressource avec des uploads
2. Cliquer sur "Supprimer" pour un fichier
3. Confirmer la suppression

**Résultat attendu** :
- ✅ Requête `DELETE /api/v1/uploads/{upload_id}` effectuée
- ✅ Status 204 No Content
- ✅ Toast de succès "Fichier supprimé"
- ✅ Le fichier disparaît de la liste
- ✅ Les caches `uploads` et `detail` sont invalidés

---

### Phase 4 : Tests Ingestion RAG

#### Test 4.1 : Déclencher l'ingestion
**Objectif** : Tester le lancement du processus d'ingestion

**Étapes** :
1. Localiser une ressource avec des uploads (status = "pending")
2. Cliquer sur le bouton "Ingérer" ou "Lancer l'ingestion"
3. Observer le changement de status

**Résultat attendu** :
- ✅ Requête `POST /api/v1/resources/{id}/ingest` effectuée
- ✅ Status 200 OK
- ✅ Réponse : `{ success: true, message: "..." }`
- ✅ Toast de succès "Ingestion RAG lancée"
- ✅ Le status de la ressource passe à "processing"
- ✅ Badge ou indicateur visuel de traitement en cours

---

#### Test 4.2 : Monitoring du status d'ingestion
**Objectif** : Vérifier le suivi de l'état d'ingestion

**Étapes** :
1. Après avoir déclenché l'ingestion
2. Rafraîchir la page (ou attendre le refetch automatique)
3. Observer l'évolution du status

**Résultat attendu** :
- ✅ Status évolue : "pending" → "processing" → "ready"
- ✅ `chunk_count` se remplit (ex: 150 chunks)
- ✅ `indexed_at` est renseigné avec une date
- ✅ Badge "Prêt" ou "Ready" s'affiche quand status="ready"

**En cas d'erreur** :
- ✅ Status = "failed"
- ✅ `error_message` contient le détail de l'erreur
- ✅ Badge "Erreur" en rouge
- ✅ Possibilité de réessayer l'ingestion

---

#### Test 4.3 : Auto-ingest à la création
**Objectif** : Tester l'ingestion automatique lors de la création

**Étapes** :
1. Créer une nouvelle ressource
2. Uploader des fichiers
3. Cocher "Auto-ingest" (si disponible dans le modal)
4. Sauvegarder

**Résultat attendu** :
- ✅ Ressource créée avec status = "processing" (pas "pending")
- ✅ L'ingestion démarre automatiquement
- ✅ Toast : "Ressource créée, ingestion en cours..."

---

### Phase 5 : Tests de Recherche et Filtres

#### Test 5.1 : Recherche par nom
**Objectif** : Tester le champ de recherche

**Étapes** :
1. Créer plusieurs ressources avec des noms différents
2. Saisir "Test" dans le champ de recherche
3. Observer le filtrage

**Résultat attendu** :
- ✅ Seules les ressources contenant "Test" s'affichent
- ✅ Le filtrage est insensible à la casse
- ✅ Le filtrage est en temps réel (pas besoin de cliquer sur "Rechercher")

---

#### Test 5.2 : Filtre enabled_only (si implémenté)
**Objectif** : Tester le filtre "Actifs uniquement"

**Étapes** :
1. Activer le filtre "Actifs uniquement"
2. Observer la requête réseau

**Résultat attendu** :
- ✅ Requête `GET /api/v1/resources?enabled_only=true`
- ✅ Seules les ressources avec `enabled=true` s'affichent

---

### Phase 6 : Tests de Gestion d'Erreurs

#### Test 6.1 : Erreur réseau (Backend down)
**Objectif** : Tester la gestion des erreurs réseau

**Étapes** :
1. Arrêter le backend
2. Tenter de charger la page `/ressources`

**Résultat attendu** :
- ✅ Message d'erreur utilisateur clair
- ✅ Pas de crash de l'application
- ✅ Toast d'erreur ou message d'erreur affiché

---

#### Test 6.2 : Erreur de validation (Backend)
**Objectif** : Tester la gestion des erreurs de validation

**Étapes** :
1. Créer une ressource avec un nom vide
2. Soumettre le formulaire

**Résultat attendu** :
- ✅ Erreur côté backend (Status 422 Unprocessable Entity)
- ✅ Toast d'erreur avec le message du backend
- ✅ Le formulaire reste ouvert

---

#### Test 6.3 : Timeout (Requête longue)
**Objectif** : Tester le timeout des requêtes

**Étapes** :
1. Simuler une ingestion très longue (> 30s)
2. Observer le comportement

**Résultat attendu** :
- ✅ Timeout après 30s (configuré dans apiClient)
- ✅ Message d'erreur approprié
- ✅ L'utilisateur peut réessayer

---

### Phase 7 : Tests de Performance et UX

#### Test 7.1 : Optimistic Updates
**Objectif** : Vérifier les mises à jour optimistes

**Étapes** :
1. Activer/désactiver une ressource
2. Observer la rapidité du changement visuel

**Résultat attendu** :
- ✅ L'interface se met à jour AVANT la réponse du serveur
- ✅ En cas d'erreur, rollback à l'état précédent
- ✅ Pas de flash ou de saut visuel

---

#### Test 7.2 : Cache React Query
**Objectif** : Vérifier la gestion du cache

**Étapes** :
1. Charger la page `/ressources`
2. Naviguer vers une autre page
3. Revenir à `/ressources` dans les 5 minutes

**Résultat attendu** :
- ✅ Les données s'affichent immédiatement (depuis le cache)
- ✅ Refetch en arrière-plan si staleTime dépassé
- ✅ React Query DevTools montre le cache

---

#### Test 7.3 : Invalidation du cache
**Objectif** : Vérifier que le cache est invalidé correctement

**Étapes** :
1. Créer une ressource
2. Observer React Query DevTools

**Résultat attendu** :
- ✅ Les query keys `['resources']` sont invalidées
- ✅ La liste se recharge automatiquement
- ✅ Les nouvelles données s'affichent

---

### Phase 8 : Tests de Régression

#### Test 8.1 : Compatibilité avec l'ancien code
**Objectif** : S'assurer qu'aucune régression n'a été introduite

**Étapes** :
1. Vérifier que les autres pages fonctionnent toujours (MCP, Agents, etc.)
2. Vérifier l'authentification
3. Vérifier le middleware

**Résultat attendu** :
- ✅ Aucun impact sur les autres modules
- ✅ L'application reste stable

---

#### Test 8.2 : Types TypeScript globaux
**Objectif** : Vérifier qu'aucune erreur TypeScript n'a été introduite

**Étapes** :
1. Exécuter `npm run build` ou `npx tsc --noEmit`
2. Observer les erreurs de compilation

**Résultat attendu** :
- ✅ Aucune erreur de compilation TypeScript
- ✅ Tous les imports sont résolus

---

## 📊 Checklist de Validation Finale

### Service Layer
- [ ] `resources.types.ts` créé et sans erreurs TypeScript
- [ ] `resources.service.ts` créé avec toutes les fonctions API
- [ ] `resources.hooks.ts` créé avec tous les hooks React Query
- [ ] Query keys correctement structurés
- [ ] Upload features intégrés (uploadFile, deleteUpload)

### UI Layer
- [ ] Page `/ressources` utilise les vrais hooks (plus de mock data)
- [ ] Tous les handlers remplacés par les mutations React Query
- [ ] États de chargement gérés (`isLoading`, `isPending`)
- [ ] Toast de succès/erreur affichés correctement

### CRUD Operations
- [ ] ✅ CREATE : Créer une ressource fonctionne
- [ ] ✅ READ : Lister les ressources fonctionne
- [ ] ✅ UPDATE : Modifier une ressource fonctionne
- [ ] ✅ DELETE : Supprimer une ressource fonctionne
- [ ] ✅ TOGGLE : Activer/désactiver fonctionne

### Upload Features
- [ ] ✅ Upload de fichiers valides fonctionne
- [ ] ✅ Rejet de fichiers invalides (type, taille)
- [ ] ✅ Suppression d'uploads fonctionne
- [ ] ✅ Liste des uploads affichée correctement

### Ingestion RAG
- [ ] ✅ Déclenchement manuel de l'ingestion fonctionne
- [ ] ✅ Suivi du status d'ingestion (pending → processing → ready)
- [ ] ✅ Gestion des erreurs d'ingestion
- [ ] ✅ Auto-ingest à la création (si implémenté)

### Error Handling
- [ ] ✅ Erreurs réseau gérées
- [ ] ✅ Erreurs de validation affichées
- [ ] ✅ Rollback des optimistic updates en cas d'erreur
- [ ] ✅ Messages d'erreur clairs pour l'utilisateur

### Performance & UX
- [ ] ✅ Optimistic updates fonctionnent
- [ ] ✅ Cache React Query configuré correctement
- [ ] ✅ Invalidation du cache après mutations
- [ ] ✅ Pas de flash ou de saut visuel

### Régression
- [ ] ✅ Aucune erreur TypeScript dans le projet
- [ ] ✅ Les autres modules fonctionnent toujours
- [ ] ✅ Build production réussi

---

## 🐛 Bugs Connus / À Investiguer

*(À remplir pendant les tests)*

### Critique
- [ ] Aucun pour le moment

### Majeur
- [ ] Aucun pour le moment

### Mineur
- [ ] Aucun pour le moment

---

## 📈 Métriques de Succès

| Métrique | Cible | Actuel | Statut |
|----------|-------|--------|--------|
| Couverture des endpoints | 100% | - | ⏳ |
| Tests CRUD passés | 5/5 | - | ⏳ |
| Tests Upload passés | 4/4 | - | ⏳ |
| Tests Ingestion passés | 3/3 | - | ⏳ |
| Erreurs TypeScript | 0 | - | ⏳ |
| Build production | ✅ | - | ⏳ |

---

## 🚀 Prochaines Étapes

Après validation de ce plan de test :

1. **Tests manuels** : Exécuter tous les tests de ce plan
2. **Documentation** : Mettre à jour la documentation utilisateur
3. **Tests automatisés** (optionnel) : Écrire des tests E2E avec Playwright/Cypress
4. **Monitoring** : Ajouter des logs pour le suivi des erreurs en production

---

## 📝 Notes

- Ce plan de test couvre l'intégration frontend/backend
- Les tests backend (unitaires, integration) sont en dehors du scope de ce document
- React Query DevTools doivent être activés en développement pour faciliter le debugging
