# Plan de Test - Module Automations

## 📋 Vue d'ensemble

Ce document décrit le plan de test complet pour le module Automations (interface READ-ONLY pilotée par IA).

**Date de création** : 2025-12-03
**Statut** : En cours
**Type d'interface** : READ-ONLY (sauf toggle enabled/disabled)

---

## 🎯 Objectifs des tests

1. Valider la couche de services (API + React Query)
2. Valider les composants UI (affichage, interactions)
3. Valider le flow complet (navigation, états, erreurs)
4. Valider l'intégration avec les données mockées

---

## 🧪 Types de tests

### 1. Tests unitaires (Services)

#### 1.1 `automations.service.ts`

**Query Keys**
- ✅ `automationKeys.all` retourne `['automations']`
- ✅ `automationKeys.lists()` retourne `['automations', 'list']`
- ✅ `automationKeys.filtered(status)` inclut le status dans la clé
- ✅ `automationKeys.detail(id)` inclut l'id dans la clé
- ✅ `automationKeys.executions(id)` est unique par automation
- ✅ `automationKeys.executionLogs(executionId)` est unique par execution

**Fonctions API**
- ✅ `getAll()` appelle `GET /automations`
- ✅ `getAll(status)` appelle `GET /automations?status={status}`
- ✅ `getById(id)` appelle `GET /automations/{id}`
- ✅ `getExecutions(id)` appelle `GET /automations/{id}/executions`
- ✅ `getExecutionLogs(executionId)` appelle `GET /executions/{executionId}/logs`
- ✅ `toggleEnabled(id, enabled)` appelle `PATCH /automations/{id}` avec `{enabled}`

**Gestion des erreurs**
- ✅ Gère les erreurs 404 (automation not found)
- ✅ Gère les erreurs 403 (not authorized)
- ✅ Gère les erreurs 500 (server error)

---

### 2. Tests d'intégration (Hooks)

#### 2.1 `automations.hooks.ts`

**useAutomations**
- ✅ Charge la liste des automations
- ✅ Gère le filtrage par status
- ✅ Affiche un loading state pendant le fetch
- ✅ Gère les erreurs API
- ✅ Met en cache les résultats

**useAutomation**
- ✅ Charge une automation par ID
- ✅ N'exécute pas si l'ID est vide
- ✅ Met en cache le résultat
- ✅ Gère les erreurs 404

**useAutomationExecutions**
- ✅ Charge les executions d'une automation
- ✅ Polling automatique si une execution est en cours
- ✅ Met en cache les résultats

**useExecutionLogs**
- ✅ Charge les logs d'une execution
- ✅ Met en cache les résultats
- ✅ Gère les erreurs si execution introuvable

**useToggleAutomation**
- ✅ Toggle l'état enabled d'une automation
- ✅ Optimistic update (UI se met à jour immédiatement)
- ✅ Rollback si l'API échoue
- ✅ Affiche un toast de succès
- ✅ Affiche un toast d'erreur en cas d'échec
- ✅ Invalide le cache après succès

---

### 3. Tests de composants UI

#### 3.1 `automation-status-badge.tsx`

**Affichage**
- ✅ Affiche "BROUILLON" pour status="draft" avec badge gris
- ✅ Affiche "ACTIVE" pour status="active" avec badge vert
- ✅ Affiche "PAUSE" pour status="paused" avec badge orange
- ✅ Affiche "ARCHIVÉE" pour status="archived" avec badge gris foncé

**Icônes**
- ✅ Affiche FileText pour draft
- ✅ Affiche Play pour active
- ✅ Affiche Pause pour paused
- ✅ Affiche Archive pour archived

---

#### 3.2 `automation-card.tsx`

**Affichage**
- ✅ Affiche le nom de l'automation
- ✅ Affiche la description (tronquée si trop longue)
- ✅ Affiche le badge de status
- ✅ Affiche les tags (si présents)
- ✅ Affiche le switch enabled/disabled
- ✅ Affiche la date de création

**Interactions**
- ✅ Clic sur la card → appelle `onClick(automation.id)`
- ✅ Clic sur le switch → appelle `onToggle(automation.id, newValue)`
- ✅ Clic sur le switch ne déclenche PAS `onClick`
- ✅ Désactive le toggle si `is_system === true`
- ✅ Affiche un tooltip "Automation système" si `is_system === true`

**États**
- ✅ Affiche un skeleton pendant le loading
- ✅ Grise la card si `enabled === false`

---

#### 3.3 `execution-timeline.tsx`

**Affichage**
- ✅ Affiche une timeline verticale
- ✅ Affiche chaque execution comme un TimelineItem
- ✅ Affiche la date/heure de l'execution
- ✅ Affiche le badge de status (pending/running/success/failed)
- ✅ Affiche les paramètres d'entrée dans un accordion

**Icônes par status**
- ✅ Clock (jaune) pour pending
- ✅ Loader2 animé (bleu) pour running
- ✅ CheckCircle2 (vert) pour success
- ✅ XCircle (rouge) pour failed

**Interactions**
- ✅ Clic sur un TimelineItem → expand l'accordion
- ✅ Affiche le JSON formaté des params
- ✅ Affiche le résultat/erreur si terminé

**Empty state**
- ✅ Affiche "Aucune execution pour le moment" si liste vide

---

#### 3.4 `execution-logs-viewer.tsx`

**Affichage**
- ✅ Affiche un accordion pour chaque step
- ✅ Affiche le nom du step + badge de niveau (INFO/WARNING/ERROR)
- ✅ Affiche le message du log
- ✅ Affiche la metadata en JSON formaté

**Filtrage**
- ✅ Select pour filtrer par niveau (ALL/INFO/WARNING/ERROR)
- ✅ Filtre correctement les logs selon le niveau sélectionné
- ✅ Input de recherche dans les messages
- ✅ Recherche insensible à la casse

**Affichage JSON**
- ✅ Syntax highlighting pour le JSON
- ✅ Scroll horizontal si le JSON est large
- ✅ Max-height avec scroll vertical

**Empty state**
- ✅ Affiche "Aucun log disponible" si liste vide

---

#### 3.5 `validation-card.tsx`

**Affichage**
- ✅ Affiche le status (pending/approved/rejected)
- ✅ Affiche la date de création
- ✅ Affiche la date de validation (si validé)
- ✅ Affiche le feedback (si présent)
- ✅ Badge avec icône selon le status

**Différence avec ToolCallCard**
- ✅ Pas de boutons d'action (READ-ONLY)
- ✅ Pas d'interactions possibles
- ✅ Design similaire mais simplifié

**Empty state**
- ✅ Affiche "Aucune validation pour le moment" si liste vide

---

#### 3.6 `automation-detail-sheet.tsx`

**Affichage général**
- ✅ Sheet s'ouvre depuis la droite
- ✅ Affiche 4 onglets (Tabs)
- ✅ Header avec le nom de l'automation
- ✅ Bouton de fermeture fonctionnel

**Onglet 1 : Informations**
- ✅ Affiche toutes les infos de l'automation (READ-ONLY)
- ✅ Affiche le badge de status
- ✅ Affiche les tags
- ✅ Affiche enabled/disabled
- ✅ Affiche permission_level
- ✅ Affiche is_system
- ✅ Affiche created_at et updated_at

**Onglet 2 : Historique**
- ✅ Affiche le composant ExecutionTimeline
- ✅ Charge les executions via le hook useAutomationExecutions
- ✅ Gère le loading state
- ✅ Gère l'empty state

**Onglet 3 : Logs**
- ✅ Select pour choisir une execution
- ✅ Affiche ExecutionLogsViewer pour l'execution sélectionnée
- ✅ Charge les logs via useExecutionLogs
- ✅ Gère le loading state
- ✅ Message "Sélectionnez une execution" si aucune sélectionnée

**Onglet 4 : Validations**
- ✅ Affiche la liste des ValidationCard
- ✅ Utilise les données mockées
- ✅ Gère l'empty state
- ✅ Note "🚧 Données mockées" visible

---

#### 3.7 `page.tsx` (Page principale)

**Affichage**
- ✅ Header avec titre "Automatisations"
- ✅ Filtres par status (Tabs: Tous, Actives, Pausées, Archivées)
- ✅ Grid de AutomationCard (responsive)
- ✅ Sheet de détails

**Chargement des données**
- ✅ Utilise le hook useAutomations
- ✅ Applique le filtre de status sélectionné
- ✅ Affiche un skeleton pendant le loading
- ✅ Affiche un message d'erreur si échec API

**Interactions**
- ✅ Clic sur un filtre → filtre les automations
- ✅ Clic sur une card → ouvre le Sheet avec l'automation
- ✅ Toggle sur une card → appelle useToggleAutomation
- ✅ Fermeture du Sheet → revient à la liste

**Empty states**
- ✅ "Aucune automation" si liste vide (général)
- ✅ "Aucune automation active" si filtre active et vide
- ✅ "Aucune automation pausée" si filtre paused et vide

**Responsive**
- ✅ Grid s'adapte (1 col mobile, 2 cols tablet, 3 cols desktop)
- ✅ Sheet prend toute la largeur sur mobile

---

## 🔄 Tests end-to-end (Flow complet)

### Scénario 1 : Consultation d'une automation

**Étapes**
1. Utilisateur navigue vers `/automatisations`
2. La liste des automations se charge
3. Utilisateur clique sur une automation
4. Le Sheet s'ouvre avec les détails
5. Utilisateur navigue entre les onglets
6. Utilisateur ferme le Sheet

**Résultat attendu**
- ✅ Aucune erreur
- ✅ Données affichées correctement
- ✅ Navigation fluide
- ✅ Fermeture propre du Sheet

---

### Scénario 2 : Toggle enabled d'une automation

**Étapes**
1. Utilisateur navigue vers `/automatisations`
2. Utilisateur clique sur le switch d'une automation
3. Le switch se met à jour (optimistic update)
4. L'API est appelée
5. Toast de succès s'affiche

**Résultat attendu**
- ✅ Switch change immédiatement
- ✅ API appelée avec le bon payload
- ✅ Toast "Automation activée/désactivée" affiché
- ✅ Cache invalidé
- ✅ Liste rechargée automatiquement

---

### Scénario 3 : Toggle échoue (rollback)

**Étapes**
1. Utilisateur navigue vers `/automatisations`
2. Utilisateur clique sur le switch
3. Le switch se met à jour
4. L'API échoue (erreur 500)
5. Rollback de l'optimistic update
6. Toast d'erreur affiché

**Résultat attendu**
- ✅ Switch revient à son état initial
- ✅ Toast d'erreur affiché
- ✅ Utilisateur peut réessayer

---

### Scénario 4 : Consultation des executions

**Étapes**
1. Utilisateur ouvre le Sheet d'une automation
2. Clique sur l'onglet "Historique"
3. Timeline des executions s'affiche
4. Utilisateur clique sur une execution
5. Accordion se déploie avec params/result

**Résultat attendu**
- ✅ Timeline affichée correctement
- ✅ Icônes selon status
- ✅ Accordion déployable
- ✅ JSON formaté lisible

---

### Scénario 5 : Consultation des logs

**Étapes**
1. Utilisateur ouvre le Sheet
2. Clique sur l'onglet "Logs"
3. Sélectionne une execution dans le select
4. Logs s'affichent
5. Utilisateur filtre par niveau "ERROR"
6. Seuls les logs ERROR s'affichent

**Résultat attendu**
- ✅ Select fonctionnel
- ✅ Logs chargés correctement
- ✅ Filtrage par niveau opérationnel
- ✅ Recherche dans les messages fonctionnelle

---

### Scénario 6 : Filtrage par status

**Étapes**
1. Utilisateur navigue vers `/automatisations`
2. Clique sur le filtre "Actives"
3. Seules les automations actives s'affichent
4. Clique sur "Archivées"
5. Seules les automations archivées s'affichent

**Résultat attendu**
- ✅ Filtrage correct
- ✅ Transitions fluides
- ✅ Empty state si filtre vide

---

## 🚧 Données mockées

**Fichier** : `src/lib/mock-data/automations-mock.ts`

### Automations mockées (3)
1. **Automation 1** : Status "active", enabled=true
2. **Automation 2** : Status "paused", enabled=false
3. **Automation 3** : Status "archived", enabled=false

### Executions mockées (10 réparties)
- 2 pending
- 1 running
- 5 success
- 2 failed

### Logs mockés (20 répartis)
- 12 INFO
- 5 WARNING
- 3 ERROR

### Validations mockées (5)
- 2 pending
- 2 approved
- 1 rejected

---

## ⚠️ Notes importantes

1. **Validations et Logs** : Actuellement mockés, seront remplacés par de vraies API calls
2. **Endpoints manquants** :
   - `GET /automations/{id}/validations`
   - Documentation détaillée dans les fichiers vides des services
3. **Polling** : Les executions en cours sont rafraîchies automatiquement toutes les 10s
4. **Toggle uniquement** : Seule interaction modifiable = switch enabled/disabled

---

## ✅ Checklist de validation

### Services
- [ ] Tous les query keys sont uniques
- [ ] Toutes les fonctions API sont implémentées
- [ ] Gestion des erreurs en place
- [ ] Types TypeScript corrects

### Hooks
- [ ] Tous les hooks fonctionnent
- [ ] Optimistic updates en place
- [ ] Cache invalidation correcte
- [ ] Toasts affichés

### Composants
- [ ] Tous les composants s'affichent
- [ ] Interactions fonctionnelles
- [ ] Empty states présents
- [ ] Loading states présents
- [ ] Responsive design

### Page
- [ ] Navigation fluide
- [ ] Filtrage opérationnel
- [ ] Sheet fonctionnel
- [ ] Aucune erreur console

### Intégration
- [ ] Flow complet fonctionne
- [ ] Données mockées affichées
- [ ] Mention "Mockées" visible
- [ ] Fichiers vides avec TODO créés

---

**Date de dernière mise à jour** : 2025-12-03
**Prochaine étape** : Implémentation des tests unitaires
