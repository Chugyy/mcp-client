# Plan de Tests - Système de Validations

## 📋 Informations Générales

**Feature** : Système de validations des tool calls
**Version** : 1.0.0
**Date** : 2025-12-03
**Type** : Tests manuels + automatisés

---

## 🎯 Objectifs des Tests

Valider que le système de validations frontend :
1. ✅ Communique correctement avec les 7 endpoints backend
2. ✅ Affiche les validations pending/approved/rejected
3. ✅ Permet d'approuver/rejeter/envoyer feedback
4. ✅ Gère le cache React Query correctement
5. ✅ Affiche les erreurs et succès avec toasts

---

## 🏗️ Architecture Testée

```
/services/validations/
├── validations.types.ts      → Types TypeScript
├── validations.service.ts    → 7 fonctions API + query keys
└── validations.hooks.ts      → 6 hooks React Query

/app/(protected)/validation/
└── page.tsx                  → Page UI refactorisée
```

---

## 🧪 Tests Unitaires (Automatisés)

### Test Suite 1 : `validations.service.test.ts`

#### Test 1.1 : Query Keys
```typescript
describe('validationKeys', () => {
  it('should generate correct query keys', () => {
    expect(validationKeys.all).toEqual(['validations'])
    expect(validationKeys.lists()).toEqual(['validations', 'list'])
    expect(validationKeys.filtered('pending')).toEqual(['validations', 'list', 'pending'])
    expect(validationKeys.detail('123')).toEqual(['validations', 'detail', '123'])
  })
})
```

#### Test 1.2 : Service API - GET
```typescript
describe('validationService.getAll', () => {
  it('should fetch all validations without filter', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockValidations })
    const result = await validationService.getAll()
    expect(mockApiClient.get).toHaveBeenCalledWith('/validations', { params: undefined })
    expect(result).toEqual(mockValidations)
  })

  it('should fetch validations filtered by status', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockValidationsPending })
    const result = await validationService.getAll('pending')
    expect(mockApiClient.get).toHaveBeenCalledWith('/validations', {
      params: { status_filter: 'pending' }
    })
    expect(result).toEqual(mockValidationsPending)
  })
})

describe('validationService.getById', () => {
  it('should fetch validation by id', async () => {
    const mockValidation = { id: '123', title: 'Test' }
    mockApiClient.get.mockResolvedValue({ data: mockValidation })
    const result = await validationService.getById('123')
    expect(mockApiClient.get).toHaveBeenCalledWith('/validations/123')
    expect(result).toEqual(mockValidation)
  })
})
```

#### Test 1.3 : Service API - CREATE
```typescript
describe('validationService.create', () => {
  it('should create a validation', async () => {
    const dto = { title: 'New', description: 'Test', source: 'api', process: 'chat' }
    const mockResponse = { id: '456', ...dto }
    mockApiClient.post.mockResolvedValue({ data: mockResponse })
    const result = await validationService.create(dto)
    expect(mockApiClient.post).toHaveBeenCalledWith('/validations', dto)
    expect(result).toEqual(mockResponse)
  })
})
```

#### Test 1.4 : Service API - ACTIONS
```typescript
describe('validationService.approve', () => {
  it('should approve validation with always_allow flag', async () => {
    const mockResponse = { success: true, message: 'Approved', stream_active: false }
    mockApiClient.post.mockResolvedValue({ data: mockResponse })
    const result = await validationService.approve('123', { always_allow: true })
    expect(mockApiClient.post).toHaveBeenCalledWith('/validations/123/approve', { always_allow: true })
    expect(result).toEqual(mockResponse)
  })
})

describe('validationService.reject', () => {
  it('should reject validation with reason', async () => {
    const mockResponse = { success: true, message: 'Rejected', stream_active: false }
    mockApiClient.post.mockResolvedValue({ data: mockResponse })
    const result = await validationService.reject('123', { reason: 'Not safe' })
    expect(mockApiClient.post).toHaveBeenCalledWith('/validations/123/reject', { reason: 'Not safe' })
    expect(result).toEqual(mockResponse)
  })
})

describe('validationService.feedback', () => {
  it('should send feedback', async () => {
    const mockResponse = { success: true, message: 'Feedback sent', stream_active: true }
    mockApiClient.post.mockResolvedValue({ data: mockResponse })
    const result = await validationService.feedback('123', { feedback: 'Please add --force flag' })
    expect(mockApiClient.post).toHaveBeenCalledWith('/validations/123/feedback', {
      feedback: 'Please add --force flag'
    })
    expect(result).toEqual(mockResponse)
  })
})
```

---

### Test Suite 2 : `validations.hooks.test.ts`

#### Test 2.1 : useValidations
```typescript
describe('useValidations', () => {
  it('should fetch all validations', async () => {
    const { result, waitFor } = renderHook(() => useValidations(), { wrapper: QueryWrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockValidations)
  })

  it('should fetch filtered validations', async () => {
    const { result, waitFor } = renderHook(() => useValidations('pending'), { wrapper: QueryWrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiClient.get).toHaveBeenCalledWith('/validations', {
      params: { status_filter: 'pending' }
    })
  })
})
```

#### Test 2.2 : useApproveValidation
```typescript
describe('useApproveValidation', () => {
  it('should approve validation and invalidate cache', async () => {
    const { result } = renderHook(() => useApproveValidation(), { wrapper: QueryWrapper })

    await act(async () => {
      result.current.mutate({ id: '123', request: { always_allow: false } })
    })

    expect(mockApiClient.post).toHaveBeenCalledWith('/validations/123/approve', { always_allow: false })
    expect(toast.success).toHaveBeenCalled()
  })

  it('should show error toast on failure', async () => {
    mockApiClient.post.mockRejectedValue({ response: { data: { detail: 'Forbidden' } } })
    const { result } = renderHook(() => useApproveValidation(), { wrapper: QueryWrapper })

    await act(async () => {
      result.current.mutate({ id: '123', request: { always_allow: false } })
    })

    expect(toast.error).toHaveBeenCalledWith('Forbidden')
  })
})
```

#### Test 2.3 : useRejectValidation
```typescript
describe('useRejectValidation', () => {
  it('should reject validation with reason', async () => {
    const { result } = renderHook(() => useRejectValidation(), { wrapper: QueryWrapper })

    await act(async () => {
      result.current.mutate({ id: '123', request: { reason: 'Unsafe operation' } })
    })

    expect(mockApiClient.post).toHaveBeenCalledWith('/validations/123/reject', { reason: 'Unsafe operation' })
    expect(toast.success).toHaveBeenCalled()
  })
})
```

#### Test 2.4 : useFeedbackValidation
```typescript
describe('useFeedbackValidation', () => {
  it('should send feedback', async () => {
    const { result } = renderHook(() => useFeedbackValidation(), { wrapper: QueryWrapper })

    await act(async () => {
      result.current.mutate({ id: '123', request: { feedback: 'Use --dry-run first' } })
    })

    expect(mockApiClient.post).toHaveBeenCalledWith('/validations/123/feedback', {
      feedback: 'Use --dry-run first'
    })
    expect(toast.success).toHaveBeenCalled()
  })
})
```

---

## 🖱️ Tests Manuels (UI)

### Prérequis
```bash
# Backend lancé sur localhost:8000
cd dev/backend && uvicorn main:app --reload

# Frontend lancé sur localhost:3000
cd dev/frontend && npm run dev

# Utilisateur authentifié
```

---

### Test Manuel 1 : Affichage Liste Validations

**Objectif** : Vérifier que les validations pending s'affichent correctement

**Steps** :
1. Naviguer vers `/validation`
2. Vérifier que la page charge sans erreur
3. Observer les ValidationCards affichées

**Résultat attendu** :
- ✅ Liste des validations pending affichées
- ✅ Chaque card affiche : titre, description, source, process, agent, date
- ✅ 3 boutons visibles : Valider, Annuler, Feedback
- ✅ Bouton "Archives" en bas à droite

**Critères d'échec** :
- ❌ Erreur 404 ou 500
- ❌ Liste vide alors qu'il y a des validations en DB
- ❌ Chargement infini

---

### Test Manuel 2 : Approuver une Validation

**Objectif** : Valider le flow d'approbation

**Steps** :
1. Cliquer sur "Valider" pour une validation
2. Vérifier que le dialog de confirmation s'ouvre
3. Lire le message : "Êtes-vous sûr de vouloir valider : [titre] ?"
4. Cliquer sur "Valider"

**Résultat attendu** :
- ✅ Dialog se ferme
- ✅ Toast success : "Validation approved and tool executed" OU "stream closed"
- ✅ La validation disparaît de la liste pending
- ✅ La validation apparaît dans les archives (cliquer bouton Archives)
- ✅ Status = "approved"

**Critères d'échec** :
- ❌ Erreur 403 (Not authorized)
- ❌ Erreur 400 (Already processed)
- ❌ Validation reste dans pending
- ❌ Pas de toast

---

### Test Manuel 3 : Rejeter une Validation

**Objectif** : Valider le flow de rejet

**Steps** :
1. Cliquer sur "Annuler" pour une validation
2. Vérifier que le dialog destructif s'ouvre
3. Lire le message : "Êtes-vous sûr de vouloir annuler : [titre] ?"
4. Cliquer sur "Annuler l'élément"

**Résultat attendu** :
- ✅ Dialog se ferme
- ✅ Toast success : "Validation rejected" OU "stream closed"
- ✅ La validation disparaît de la liste pending
- ✅ La validation apparaît dans les archives avec status "rejected"

**Critères d'échec** :
- ❌ Erreur backend
- ❌ Validation reste pending

---

### Test Manuel 4 : Envoyer un Feedback

**Objectif** : Valider le flow de feedback

**Steps** :
1. Cliquer sur "Feedback" pour une validation
2. Vérifier que le FeedbackDialog s'ouvre
3. Taper un feedback : "Please use --dry-run flag first"
4. Cliquer sur "Envoyer"

**Résultat attendu** :
- ✅ Dialog se ferme
- ✅ Toast success : "Feedback submitted" OU "stream closed, send a new message to continue"
- ✅ La validation change de status vers "feedback"
- ✅ Si stream actif : le LLM reçoit le feedback et peut répondre

**Critères d'échec** :
- ❌ Dialog ne se ferme pas
- ❌ Feedback non envoyé au backend
- ❌ Status reste "pending"

---

### Test Manuel 5 : Archives Sidebar

**Objectif** : Vérifier l'affichage des validations archivées

**Steps** :
1. Cliquer sur le bouton "Archives" (bottom-right)
2. Observer la sidebar qui s'ouvre depuis la droite
3. Vérifier que les validations approved/rejected s'affichent
4. Fermer la sidebar

**Résultat attendu** :
- ✅ Sidebar s'ouvre avec animation
- ✅ Liste des validations approved/rejected affichées
- ✅ Badge de status visible (approved = vert, rejected = rouge)
- ✅ Possible de fermer la sidebar

**Critères d'échec** :
- ❌ Sidebar vide alors qu'il y a des archives
- ❌ Erreur lors du fetch

---

### Test Manuel 6 : Gestion des Erreurs

**Objectif** : Vérifier les messages d'erreur

**Test 6.1 : Validation déjà traitée**
1. Ouvrir 2 onglets sur `/validation`
2. Dans onglet 1 : approuver une validation
3. Dans onglet 2 : essayer d'approuver la même validation

**Résultat attendu** :
- ✅ Toast error : "Validation already approved"
- ✅ La validation disparaît après refresh

**Test 6.2 : Backend down**
1. Arrêter le backend
2. Essayer d'approuver une validation

**Résultat attendu** :
- ✅ Toast error : "Erreur lors de l'approbation"
- ✅ Page ne crash pas

---

### Test Manuel 7 : Cache React Query

**Objectif** : Vérifier que le cache fonctionne

**Steps** :
1. Ouvrir `/validation`
2. Observer les validations chargées
3. Naviguer vers `/chat`
4. Revenir sur `/validation`

**Résultat attendu** :
- ✅ Les validations s'affichent instantanément (depuis cache)
- ✅ Refetch en background (voir React Query DevTools)
- ✅ Pas de loading spinner si données en cache

---

### Test Manuel 8 : Stream Actif (Intégration)

**Objectif** : Tester l'intégration avec le stream chat

**Prérequis** : Avoir un stream actif dans `/chat` qui demande une validation

**Steps** :
1. Dans `/chat`, envoyer un message qui trigger un tool call nécessitant validation
2. Observer l'event SSE `validation_required` avec validation_id
3. Naviguer vers `/validation`
4. Approuver la validation
5. Observer que le stream reprend automatiquement dans `/chat`

**Résultat attendu** :
- ✅ Toast : "Validation approved and tool executed"
- ✅ stream_active: true dans la réponse
- ✅ Le résultat du tool est injecté dans le stream
- ✅ Le LLM continue sa réponse

**Critères d'échec** :
- ❌ stream_active: false alors que chat ouvert
- ❌ Le stream ne reprend pas
- ❌ Le tool n'est pas exécuté

---

## 📊 Checklist Complète

### Backend (à vérifier côté API)
- [ ] Endpoint `GET /validations` retourne 200
- [ ] Endpoint `GET /validations?status_filter=pending` filtre correctement
- [ ] Endpoint `GET /validations/{id}` retourne 200 ou 404
- [ ] Endpoint `POST /validations` crée une validation
- [ ] Endpoint `PATCH /validations/{id}/status` met à jour
- [ ] Endpoint `POST /validations/{id}/approve` exécute le tool
- [ ] Endpoint `POST /validations/{id}/reject` rejette
- [ ] Endpoint `POST /validations/{id}/feedback` envoie feedback

### Frontend - Architecture
- [ ] `validations.types.ts` définit tous les types
- [ ] `validations.service.ts` implémente les 7 fonctions
- [ ] `validations.hooks.ts` crée les 6 hooks
- [ ] Pas d'erreurs TypeScript (`npm run type-check`)
- [ ] Imports corrects dans `page.tsx`

### Frontend - Fonctionnalités
- [ ] Liste validations pending affichée
- [ ] Bouton "Valider" fonctionne
- [ ] Bouton "Annuler" fonctionne
- [ ] Bouton "Feedback" fonctionne
- [ ] Archives sidebar fonctionne
- [ ] Toasts success/error affichés
- [ ] Cache React Query fonctionne
- [ ] Gestion erreurs 400/403/404/500

### Frontend - UI/UX
- [ ] Loading states corrects
- [ ] Animations smooth
- [ ] Responsive design OK
- [ ] Accessibilité (aria-labels)
- [ ] Pas de memory leaks

---

## 🐛 Bugs Potentiels à Surveiller

### Bug #1 : Race Condition sur Cache
**Symptôme** : Après approve, la validation réapparaît brièvement
**Cause** : Invalidation cache trop lente
**Fix** : Utiliser optimistic update

### Bug #2 : Toast en Double
**Symptôme** : 2 toasts success affichés
**Cause** : Hook appelé 2 fois (React strict mode)
**Fix** : Vérifier que `onSuccess` n'est pas dupliqué

### Bug #3 : Stream Actif Non Détecté
**Symptôme** : stream_active=false alors que chat ouvert
**Cause** : Backend ne détecte pas le stream actif
**Fix** : Vérifier `stream_manager.is_stream_active()`

---

## 📈 Métriques de Performance

### Temps de Chargement
- [ ] Page `/validation` charge en < 500ms (cache)
- [ ] Première requête API en < 1s
- [ ] Approve/reject action en < 2s

### Optimisation
- [ ] Pas de re-renders inutiles (React DevTools Profiler)
- [ ] Query keys correctement configurées
- [ ] StaleTime configuré (5 min par défaut)

---

## ✅ Critères de Validation Globale

**Le test est validé si** :
1. ✅ Tous les tests unitaires passent (npm test)
2. ✅ Tous les tests manuels passent
3. ✅ Pas d'erreurs TypeScript
4. ✅ Pas d'erreurs console
5. ✅ Performance acceptable (< 2s pour approve)
6. ✅ Code review validé (respect architecture)

---

## 📝 Notes pour Testeur

- Utiliser React Query DevTools pour debugger le cache
- Utiliser Network tab pour inspecter les requêtes API
- Tester avec un backend réel (pas de mocks en tests manuels)
- Tester sur Chrome + Firefox + Safari
- Tester en mode production (`npm run build && npm start`)

---

**Version** : 1.0.0
**Dernière mise à jour** : 2025-12-03
**Prochaine révision** : Après implémentation automatisations validations
