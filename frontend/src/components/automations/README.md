# Composants Automations

Ce dossier contient les composants React pour le module Automations.

## Composants disponibles

### 1. `ExecutionTimeline`

Timeline verticale affichant l'historique des executions d'une automation.

**Props:**
- `executions: Execution[]` - Liste des executions à afficher

**Fonctionnalités:**
- Affichage chronologique des executions
- Badges de statut colorés (EN ATTENTE, EN COURS, TERMINÉ, ÉCHEC)
- Accordion pour afficher les détails de chaque execution
- Affichage des paramètres, résultats et erreurs au format JSON
- Calcul automatique de la durée d'execution
- Empty state quand aucune execution

**Exemple d'utilisation:**
```tsx
import { ExecutionTimeline } from '@/components/automations'
import { getExecutionsByAutomationId } from '@/lib/mock-data/automations-mock'

export function AutomationExecutionsPage({ automationId }: { automationId: string }) {
  const executions = getExecutionsByAutomationId(automationId)

  return (
    <div className="container mx-auto py-8">
      <h2 className="text-2xl font-bold mb-6">Historique des executions</h2>
      <ExecutionTimeline executions={executions} />
    </div>
  )
}
```

---

### 2. `ExecutionLogsViewer`

Affichage des logs d'une execution avec filtrage par niveau et recherche.

**Props:**
- `logs: ExecutionLog[]` - Liste des logs à afficher

**Fonctionnalités:**
- Filtrage par niveau (INFO, WARNING, ERROR)
- Recherche textuelle dans les messages et noms d'étapes
- Affichage des métadonnées au format JSON
- Accordion pour voir les détails de chaque log
- ScrollArea pour gérer les listes longues
- Empty state quand aucun log ou résultat de recherche vide

**Exemple d'utilisation:**
```tsx
import { ExecutionLogsViewer } from '@/components/automations'
import { getLogsByExecutionId } from '@/lib/mock-data/automations-mock'

export function ExecutionLogsPage({ executionId }: { executionId: string }) {
  const logs = getLogsByExecutionId(executionId)

  return (
    <div className="container mx-auto py-8">
      <h2 className="text-2xl font-bold mb-6">Logs d'execution</h2>
      <ExecutionLogsViewer logs={logs} />
    </div>
  )
}
```

---

### 3. `ValidationCard` et `ValidationList`

Affichage des validations d'automations en lecture seule (READ-ONLY).

**Props pour ValidationCard:**
- `validation: AutomationValidation` - La validation à afficher

**Props pour ValidationList:**
- `validations: AutomationValidation[]` - Liste des validations à afficher

**Fonctionnalités:**
- Affichage READ-ONLY (pas de boutons d'action)
- Badges de statut colorés (EN ATTENTE, APPROUVÉE, REJETÉE)
- Accordion pour afficher les détails de chaque validation
- Affichage de l'execution_id associée
- Dates formatées en français avec date-fns
- Affichage du feedback si présent
- Empty state quand aucune validation
- Note visible sur les données mockées

**Exemple d'utilisation:**
```tsx
import { ValidationList } from '@/components/automations'
import { getValidationsByAutomationId } from '@/lib/mock-data/automations-mock'

export function AutomationValidationsPage({ automationId }: { automationId: string }) {
  const validations = getValidationsByAutomationId(automationId)

  return (
    <div className="container mx-auto py-8">
      <h2 className="text-2xl font-bold mb-6">Validations</h2>
      <ValidationList validations={validations} />
    </div>
  )
}
```

---

### 4. `AutomationCard`

Carte d'affichage d'une automation (composant existant).

---

### 5. `AutomationStatusBadge`

Badge de statut pour une automation (composant existant).

---

### 6. `AutomationDetailSheet`

Sheet (panneau latéral) affichant tous les détails d'une automation avec 4 onglets.

**Props:**
- `automationId: string | null` - ID de l'automation à afficher
- `open: boolean` - État d'ouverture du sheet
- `onOpenChange: (open: boolean) => void` - Callback pour gérer la fermeture

**Fonctionnalités:**
- 4 onglets : Infos, Historique, Logs, Validations
- Utilise les hooks React Query (`useAutomation`, `useAutomationExecutions`)
- Gestion des états de chargement avec Skeleton
- Sélection d'execution pour afficher les logs correspondants
- Intégration de tous les composants : `AutomationStatusBadge`, `ExecutionTimeline`, `ExecutionLogsViewer`, `ValidationList`
- Empty states pour chaque onglet
- Formatage des dates en français
- Affichage de toutes les infos de l'automation en READ-ONLY

**Onglet 1 - Infos:**
- Status et état (activé/désactivé)
- Tags
- Niveau de permission
- Indicateur d'automation système
- Dates de création et mise à jour
- IDs (automation ID et user ID)

**Onglet 2 - Historique:**
- Timeline complète des executions via `ExecutionTimeline`

**Onglet 3 - Logs:**
- Sélecteur d'execution
- Affichage des logs via `ExecutionLogsViewer`
- Note sur les données mockées

**Onglet 4 - Validations:**
- Liste des validations via `ValidationList`

**Exemple d'utilisation:**
```tsx
import { AutomationDetailSheet } from '@/components/automations'
import { useState } from 'react'

export function AutomationsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  const handleOpenDetails = (automationId: string) => {
    setSelectedId(automationId)
    setSheetOpen(true)
  }

  return (
    <div>
      {/* Liste d'automations */}
      <button onClick={() => handleOpenDetails('auto_001')}>
        Voir détails
      </button>

      {/* Sheet de détails */}
      <AutomationDetailSheet
        automationId={selectedId}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
      />
    </div>
  )
}
```

---

## Données mockées

Les données mockées sont disponibles dans `/src/lib/mock-data/automations-mock.ts` :

```tsx
import {
  mockAutomations,
  mockExecutions,
  mockExecutionLogs,
  mockValidations,
  getExecutionsByAutomationId,
  getLogsByExecutionId,
  getValidationsByAutomationId
} from '@/lib/mock-data/automations-mock'
```

## Composants UI utilisés

Ces composants utilisent les composants Shadcn UI suivants :
- `Timeline` (custom)
- `Accordion`
- `Badge`
- `Input`
- `Select`
- `ScrollArea`

## Dépendances

- `date-fns` pour le formatage des dates en français
- `lucide-react` pour les icônes
