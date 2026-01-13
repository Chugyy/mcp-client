# Plan de Tests - Service Agents

## 📋 Vue d'ensemble

Ce document détaille le plan de tests complet pour l'implémentation du service Agents suivant l'architecture API React Query + Axios.

---

## 🎯 Objectifs des tests

1. **Fiabilité** : Garantir que toutes les opérations CRUD fonctionnent correctement
2. **Type-safety** : Valider que les types TypeScript sont correctement définis et utilisés
3. **Gestion du cache** : Vérifier que React Query gère correctement le cache et les invalidations
4. **UX** : S'assurer que les états de chargement, erreurs et succès sont bien gérés
5. **Sécurité** : Valider que les autorisations sont respectées (user_id, is_system)

---

## 📁 Structure des tests

```
dev/frontend/doc/tests/agents/
├── TEST_PLAN.md                    # Ce fichier
├── unit/
│   ├── types.test.md               # Tests des interfaces TypeScript
│   ├── service.test.md             # Tests du service API
│   └── hooks.test.md               # Tests des hooks React Query
├── integration/
│   └── agents-flow.test.md         # Tests d'intégration du flux complet
└── e2e/
    └── agents-page.test.md         # Tests end-to-end de la page
```

---

## 🧪 Tests unitaires

### 1. Tests des types (`agents.types.ts`)

**Fichier** : `unit/types.test.md`

#### Test 1.1 : Validation de l'interface `Agent`
- ✅ Vérifier que `Agent` contient tous les champs obligatoires : `id`, `name`, `user_id`, `created_at`, `updated_at`
- ✅ Vérifier que `Agent` contient les champs optionnels : `description`, `system_prompt`, `tags`, `enabled`, `is_system`
- ✅ Vérifier que `tags` est typé comme `string[]`
- ✅ Vérifier que `enabled` et `is_system` sont des booléens

#### Test 1.2 : Validation de `CreateAgentDTO`
- ✅ Vérifier que `name` est obligatoire (string)
- ✅ Vérifier que `description`, `system_prompt`, `tags`, `enabled` sont optionnels
- ✅ Vérifier que les types correspondent aux attentes du backend

#### Test 1.3 : Validation de `UpdateAgentDTO`
- ✅ Vérifier que tous les champs sont optionnels (`Partial`)
- ✅ Vérifier que les types correspondent à `Agent`

---

### 2. Tests du service (`agents.service.ts`)

**Fichier** : `unit/service.test.md`

#### Test 2.1 : Query Keys
- ✅ `agentKeys.all` retourne `['agents']`
- ✅ `agentKeys.lists()` retourne `['agents', 'list']`
- ✅ `agentKeys.detail('123')` retourne `['agents', 'detail', '123']`

#### Test 2.2 : `agentService.getAll()`
- ✅ Appelle `GET /agents` avec le bon client Axios
- ✅ Retourne un tableau d'agents typé `Agent[]`
- ✅ Gère les erreurs HTTP (401, 500)

#### Test 2.3 : `agentService.getById(id)`
- ✅ Appelle `GET /agents/{id}` avec l'ID fourni
- ✅ Retourne un agent typé `Agent`
- ✅ Gère les erreurs 404, 403

#### Test 2.4 : `agentService.create(dto)`
- ✅ Appelle `POST /agents` avec le DTO
- ✅ Envoie les bons headers (Content-Type, Authorization)
- ✅ Retourne l'agent créé typé `Agent`
- ✅ Gère les erreurs de validation (400)

#### Test 2.5 : `agentService.update(id, dto)`
- ✅ Appelle `PATCH /agents/{id}` avec le DTO
- ✅ Retourne l'agent mis à jour
- ✅ Gère les erreurs 403, 404, 500

#### Test 2.6 : `agentService.delete(id)`
- ✅ Appelle `DELETE /agents/{id}`
- ✅ Retourne `void`
- ✅ Gère les erreurs 403 (agent système), 404

---

### 3. Tests des hooks (`agents.hooks.ts`)

**Fichier** : `unit/hooks.test.md`

#### Test 3.1 : `useAgents()`
- ✅ Utilise la bonne query key (`agentKeys.lists()`)
- ✅ Appelle `agentService.getAll()` comme queryFn
- ✅ Retourne `data`, `isLoading`, `error`, `refetch`
- ✅ Cache les données correctement
- ✅ Réagit au stale time (5 min)

#### Test 3.2 : `useAgent(id)`
- ✅ Utilise la bonne query key (`agentKeys.detail(id)`)
- ✅ Appelle `agentService.getById(id)` comme queryFn
- ✅ `enabled: !!id` → ne lance pas la requête si `id` est vide
- ✅ Retourne les bonnes données

#### Test 3.3 : `useCreateAgent()`
- ✅ Appelle `agentService.create(dto)` via `mutationFn`
- ✅ `onSuccess` invalide `agentKeys.all`
- ✅ `onSuccess` affiche un toast de succès
- ✅ `onError` affiche un toast d'erreur
- ✅ Retourne `mutate`, `isPending`, `isSuccess`, `isError`

#### Test 3.4 : `useUpdateAgent()`
- ✅ Appelle `agentService.update(id, data)` via `mutationFn`
- ✅ Implémente un optimistic update dans `onMutate`
- ✅ `onMutate` annule les queries en cours
- ✅ `onMutate` met à jour le cache optimistiquement
- ✅ `onError` restaure les données précédentes (rollback)
- ✅ `onSuccess` invalide `agentKeys.all` et affiche un toast
- ✅ Gère correctement le context pour le rollback

#### Test 3.5 : `useDeleteAgent()`
- ✅ Appelle `agentService.delete(id)` via `mutationFn`
- ✅ `onSuccess` invalide `agentKeys.all`
- ✅ `onSuccess` affiche un toast de succès
- ✅ `onError` affiche un toast d'erreur avec le bon message
- ✅ Gère l'erreur 403 pour les agents système

---

## 🔗 Tests d'intégration

### 4. Flux complet CRUD

**Fichier** : `integration/agents-flow.test.md`

#### Test 4.1 : Flux de création complet
1. ✅ L'utilisateur charge la page → `useAgents()` fetch la liste
2. ✅ L'utilisateur clique sur "Créer" → `useCreateAgent()` est appelé
3. ✅ Le toast de succès s'affiche
4. ✅ Le cache est invalidé → `useAgents()` refetch automatiquement
5. ✅ Le nouvel agent apparaît dans la liste

#### Test 4.2 : Flux de mise à jour avec optimistic update
1. ✅ La liste des agents est affichée
2. ✅ L'utilisateur toggle `enabled` → `useUpdateAgent()` est appelé
3. ✅ L'UI se met à jour immédiatement (optimistic)
4. ✅ La requête PATCH est envoyée
5. ✅ Si succès → Le cache est invalidé
6. ✅ Si erreur → Rollback vers l'état précédent + toast d'erreur

#### Test 4.3 : Flux de suppression
1. ✅ L'utilisateur clique sur "Supprimer"
2. ✅ Confirmation (optionnelle)
3. ✅ `useDeleteAgent()` est appelé
4. ✅ Si agent système → Erreur 403 + toast explicite
5. ✅ Si succès → Cache invalidé + toast + agent retiré de la liste

#### Test 4.4 : Gestion des erreurs réseau
1. ✅ L'API est down → `useAgents()` affiche une erreur
2. ✅ L'utilisateur tente de créer → `useCreateAgent()` échoue + toast
3. ✅ Le retry automatique de React Query fonctionne (1 retry)

#### Test 4.5 : Gestion des autorisations
1. ✅ L'utilisateur accède à un agent qui ne lui appartient pas → 403
2. ✅ L'utilisateur tente de supprimer un agent système → 403 + message clair
3. ✅ L'utilisateur tente de modifier un agent d'un autre user → 403

---

## 🌐 Tests end-to-end

### 5. Tests de la page agents

**Fichier** : `e2e/agents-page.test.md`

#### Test 5.1 : Chargement initial de la page
- ✅ La page affiche un loader pendant le chargement
- ✅ La liste des agents s'affiche après le fetch
- ✅ Si aucun agent → Message "Aucun agent"
- ✅ Si erreur → Message d'erreur clair

#### Test 5.2 : Affichage de la liste
- ✅ Chaque agent affiche : `name`, `description`, `tags`, `enabled`
- ✅ Les tags sont affichés visuellement (chips/badges)
- ✅ Le statut `enabled` est visible (toggle ou badge)
- ✅ Les agents système ont un indicateur visuel distinct

#### Test 5.3 : Formulaire de création
- ✅ Le bouton "Créer un agent" ouvre un formulaire/modal
- ✅ Le formulaire contient : `name*`, `description`, `system_prompt`, `tags`, `enabled`
- ✅ La validation des champs fonctionne (name obligatoire)
- ✅ Lors de la soumission → Loader + désactivation du bouton
- ✅ Si succès → Toast + formulaire fermé + liste mise à jour
- ✅ Si erreur → Toast d'erreur + formulaire reste ouvert

#### Test 5.4 : Édition d'un agent
- ✅ Le bouton "Éditer" ouvre un formulaire pré-rempli
- ✅ Les modifications sont sauvegardées avec `useUpdateAgent()`
- ✅ L'optimistic update fonctionne (UI réactive)
- ✅ Si erreur → Rollback + toast

#### Test 5.5 : Suppression d'un agent
- ✅ Le bouton "Supprimer" affiche une confirmation
- ✅ Si agent système → Désactivation du bouton ou message d'avertissement
- ✅ Si confirmation → `useDeleteAgent()` appelé
- ✅ Si succès → Agent retiré de la liste + toast
- ✅ Si erreur → Toast avec message explicite

#### Test 5.6 : Toggle enabled/disabled
- ✅ Le toggle change l'état immédiatement (optimistic)
- ✅ La requête PATCH est envoyée
- ✅ Si erreur → Rollback + toast

#### Test 5.7 : Gestion des états de chargement
- ✅ Pendant `isLoading` → Skeleton ou spinner
- ✅ Pendant `isPending` (mutation) → Bouton désactivé + loader
- ✅ Après succès → Retour à l'état normal

#### Test 5.8 : Gestion des erreurs
- ✅ Erreur 401 (non authentifié) → Redirection vers login
- ✅ Erreur 403 → Message "Non autorisé"
- ✅ Erreur 404 → Message "Agent non trouvé"
- ✅ Erreur 500 → Message générique + possibilité de retry

---

## 🛠️ Outils de test recommandés

### Tests unitaires
- **Vitest** : Framework de test rapide pour TypeScript
- **@testing-library/react** : Pour tester les hooks React
- **msw** (Mock Service Worker) : Pour mocker les appels API

### Tests d'intégration
- **React Testing Library** : Pour tester les composants avec les hooks
- **@tanstack/react-query/testing** : Helpers pour tester React Query

### Tests E2E
- **Playwright** ou **Cypress** : Pour tester le flux complet dans le navigateur

---

## ✅ Critères de validation

### Phase 1 : Tests unitaires (OBLIGATOIRE avant déploiement)
- [ ] Tous les tests de `types.test.md` passent
- [ ] Tous les tests de `service.test.md` passent
- [ ] Tous les tests de `hooks.test.md` passent
- [ ] Couverture de code > 80%

### Phase 2 : Tests d'intégration (OBLIGATOIRE avant déploiement)
- [ ] Tous les flux CRUD fonctionnent correctement
- [ ] Les optimistic updates fonctionnent sans bug
- [ ] Les erreurs sont gérées proprement

### Phase 3 : Tests E2E (RECOMMANDÉ avant production)
- [ ] La page se charge correctement
- [ ] Toutes les interactions utilisateur fonctionnent
- [ ] Les toasts s'affichent au bon moment
- [ ] La page est responsive

---

## 📊 Checklist de déploiement

Avant de considérer l'implémentation comme terminée :

- [ ] Les 3 fichiers de service sont créés (types, service, hooks)
- [ ] La page `agents/page.tsx` utilise les hooks
- [ ] Les tests unitaires passent
- [ ] Les tests d'intégration passent
- [ ] La documentation est à jour
- [ ] Les types TypeScript sont stricts (pas de `any`)
- [ ] Les erreurs affichent des messages clairs
- [ ] Le cache React Query fonctionne correctement
- [ ] Les optimistic updates sont fluides
- [ ] Les toasts sont appropriés (succès, erreur)

---

## 🎯 Tests manuels recommandés

### Scénarios manuels à tester
1. **Créer 5 agents successifs** → Vérifier que la liste se met à jour
2. **Modifier le même agent 3 fois rapidement** → Vérifier l'optimistic update
3. **Supprimer un agent puis refetch** → Vérifier qu'il a bien disparu
4. **Couper le réseau et tenter une action** → Vérifier la gestion d'erreur
5. **Ouvrir 2 onglets et modifier un agent** → Vérifier la synchronisation du cache

---

## 📝 Notes de test

### Points d'attention particuliers
- **Tags** : Vérifier que les tags sont bien sérialisés/désérialisés (array de strings)
- **Agents système** : Ne jamais permettre la suppression d'un agent `is_system: true`
- **Autorisations** : Un user ne doit voir que ses agents (sauf agents système)
- **Optimistic updates** : Bien tester le rollback en cas d'erreur réseau

### Cas limites à tester
- Agent sans description (null vs "")
- Agent sans tags ([] vs undefined)
- Agent avec un nom très long (>255 caractères)
- Création d'agent avec des caractères spéciaux dans le nom
- Tentative de suppression d'un agent déjà supprimé (404)

---

## 🚀 Conclusion

Ce plan de tests garantit une implémentation robuste et maintenable du service Agents. Chaque test doit être exécuté et validé avant de passer à l'étape suivante.

**Prochaine étape** : Implémentation du code en suivant le plan d'action et le plan de délégation.
