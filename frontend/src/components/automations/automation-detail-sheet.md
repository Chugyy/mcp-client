# AutomationDetailSheet

**Fichier:** `/src/components/automations/automation-detail-sheet.tsx`

## Description

Composant Sheet (panneau latéral) affichant tous les détails d'une automation avec 4 onglets : Infos, Historique, Logs et Validations.

## Props

```typescript
interface AutomationDetailSheetProps {
  automationId: string | null      // ID de l'automation à afficher
  open: boolean                     // État d'ouverture du sheet
  onOpenChange: (open: boolean) => void  // Callback pour gérer la fermeture/ouverture
}
```

## Structure des onglets

### 1. Onglet "Infos" (READ-ONLY)

Affiche toutes les informations de l'automation :

- **Status et état** : Badge de status + indicateur activé/désactivé
- **Tags** : Liste des tags avec badges
- **Permissions** : Niveau de permission + indicateur système
- **Dates** : Date de création et dernière mise à jour (formaté en français)
- **IDs** : automation_id et user_id

### 2. Onglet "Historique"

- Utilise le composant `ExecutionTimeline`
- Affiche la timeline complète des executions
- Empty state si aucune execution

### 3. Onglet "Logs"

- Sélecteur d'execution (Select dropdown)
- Affiche les logs via `ExecutionLogsViewer`
- Note visible sur les données mockées
- Empty state si aucune execution sélectionnée

### 4. Onglet "Validations"

- Utilise le composant `ValidationList`
- Affiche toutes les validations liées à l'automation
- Mode READ-ONLY

## Hooks React Query utilisés

```typescript
// Récupère les détails de l'automation
const { data: automation, isLoading: isLoadingAutomation } = useAutomation(automationId || '')

// Récupère l'historique des executions
const { data: executions, isLoading: isLoadingExecutions } = useAutomationExecutions(automationId || '')
```

## Données mockées

Pour le moment, les logs et validations utilisent les fonctions helper mockées :

```typescript
// Logs (remplacera useExecutionLogs quand backend sera prêt)
const logs = selectedExecutionId ? getLogsByExecutionId(selectedExecutionId) : []

// Validations
const validations = automationId ? getValidationsByAutomationId(automationId) : []
```

## États de chargement

Le composant gère les états de chargement avec des `Skeleton` :
- Skeleton pour le titre et la description
- Skeleton pour les blocs d'informations (onglet Infos)
- Skeleton pour les executions (onglet Historique)

## Empty states

Chaque onglet a son empty state :
- **Historique** : "Aucune execution pour le moment"
- **Logs** : "Sélectionnez une execution pour afficher ses logs"
- **Validations** : Géré par `ValidationList`

## Exemple d'utilisation

### Usage basique

```tsx
'use client'

import { useState } from 'react'
import { AutomationDetailSheet } from '@/components/automations'

export function AutomationsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  const handleViewDetails = (automationId: string) => {
    setSelectedId(automationId)
    setSheetOpen(true)
  }

  return (
    <div>
      <button onClick={() => handleViewDetails('auto_001')}>
        Voir automation 001
      </button>

      <AutomationDetailSheet
        automationId={selectedId}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
      />
    </div>
  )
}
```

### Avec une liste d'automations

```tsx
'use client'

import { useState } from 'react'
import { AutomationCard, AutomationDetailSheet } from '@/components/automations'
import { useAutomations } from '@/services/automations/automations.hooks'

export function AutomationsListPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  const { data: automations = [], isLoading } = useAutomations()

  const handleOpenSheet = (automationId: string) => {
    setSelectedId(automationId)
    setSheetOpen(true)
  }

  return (
    <div className="container mx-auto py-8">
      <div className="grid gap-4">
        {automations.map((automation) => (
          <AutomationCard
            key={automation.id}
            automation={automation}
            onViewDetails={() => handleOpenSheet(automation.id)}
          />
        ))}
      </div>

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

## Composants utilisés

### Composants UI Shadcn

- `Sheet`, `SheetContent`, `SheetHeader`, `SheetTitle`, `SheetDescription`
- `Tabs`, `TabsContent`, `TabsList`, `TabsTrigger`
- `Badge`
- `Skeleton`
- `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue`

### Composants Automations

- `AutomationStatusBadge`
- `ExecutionTimeline`
- `ExecutionLogsViewer`
- `ValidationList`

### Icônes (lucide-react)

- `Shield` : Indicateur d'automation système
- `Calendar` : Section dates
- `Tag` : Section tags

## Dépendances

- `react` : useState hook
- `date-fns` + `date-fns/locale` : Formatage des dates en français
- `@tanstack/react-query` : Hooks `useAutomation` et `useAutomationExecutions`

## Notes importantes

1. **READ-ONLY** : Ce composant est en lecture seule. Pas de boutons d'édition ou d'action.

2. **Données mockées** : Les logs et validations utilisent temporairement les données mockées. Migration vers les vrais hooks React Query à venir.

3. **Responsive** : Le sheet utilise `sm:max-w-2xl` pour s'adapter aux écrans larges.

4. **Refetch automatique** : Les executions sont refetch automatiquement toutes les 10s si une execution est en cours (géré par `useAutomationExecutions`).

5. **Protection null** : Le composant retourne `null` si `automationId` est null.

## Fichiers liés

- `/src/components/automations/automation-detail-sheet.tsx` : Composant principal
- `/src/components/automations/automation-detail-sheet.demo.tsx` : Fichier de démonstration
- `/src/services/automations/automations.hooks.ts` : Hooks React Query
- `/src/lib/mock-data/automations-mock.ts` : Données mockées temporaires

## Tests manuels

Pour tester le composant avec les données mockées :

```tsx
import { AutomationDetailSheetDemo } from '@/components/automations/automation-detail-sheet.demo'

// Dans votre page
<AutomationDetailSheetDemo />
```

Les IDs mockés disponibles : `auto_001`, `auto_002`, `auto_003`
