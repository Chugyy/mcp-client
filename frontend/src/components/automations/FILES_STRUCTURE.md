# Structure des fichiers Automations

## Arborescence complète

```
src/components/automations/
├── automation-card.tsx                    # Carte d'affichage d'une automation
├── automation-status-badge.tsx            # Badge de status
├── execution-timeline.tsx                 # Timeline des executions
├── execution-logs-viewer.tsx              # Viewer de logs
├── validation-card.tsx                    # Card + List des validations
├── automation-detail-sheet.tsx            # ⭐ COMPOSANT PRINCIPAL (nouveau)
├── automation-detail-sheet.demo.tsx       # Composant de démo (nouveau)
├── automation-detail-sheet.md             # Documentation complète (nouveau)
├── INTEGRATION_EXAMPLE.tsx                # Exemples d'intégration (nouveau)
├── FILES_STRUCTURE.md                     # Ce fichier (nouveau)
├── index.ts                               # Exports centralisés (modifié)
└── README.md                              # Documentation globale (modifié)
```

## Description des fichiers

### Fichiers principaux

#### `automation-detail-sheet.tsx` (243 lignes)
**Composant principal créé**

- Panneau latéral (Sheet) avec 4 onglets
- Intègre tous les composants précédents
- Utilise React Query pour les données
- Gestion complète des loading et empty states

**Props:**
```typescript
{
  automationId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}
```

**Onglets:**
1. **Infos** - Toutes les informations de l'automation (READ-ONLY)
2. **Historique** - Timeline des executions
3. **Logs** - Logs d'une execution sélectionnée
4. **Validations** - Liste des validations

#### `automation-card.tsx`
Carte d'affichage d'une automation dans une liste

#### `automation-status-badge.tsx`
Badge de status coloré (draft, active, paused, archived)

#### `execution-timeline.tsx`
Timeline verticale affichant l'historique des executions

#### `execution-logs-viewer.tsx`
Affichage des logs avec filtrage et recherche

#### `validation-card.tsx`
Carte et liste des validations (READ-ONLY)

### Fichiers de documentation

#### `automation-detail-sheet.md`
Documentation complète du composant AutomationDetailSheet :
- Description détaillée
- Props et types
- Structure des onglets
- Hooks utilisés
- Exemples d'utilisation
- Notes importantes

#### `INTEGRATION_EXAMPLE.tsx`
Exemples complets d'intégration :
- Intégration avec liste d'automations
- Version avec données mockées
- Version avec table
- Handlers et state management

#### `README.md`
Documentation globale du dossier automations :
- Liste de tous les composants
- Exemples d'utilisation
- Données mockées
- Dépendances

#### `FILES_STRUCTURE.md`
Ce fichier - Structure et organisation des fichiers

### Fichiers de démonstration

#### `automation-detail-sheet.demo.tsx`
Composant de démonstration pour tester AutomationDetailSheet rapidement :
- Boutons pour ouvrir les 3 automations mockées
- Permet de tester tous les onglets
- Utilise les données mockées

### Fichier d'exports

#### `index.ts`
Exports centralisés de tous les composants :
```typescript
export { AutomationCard } from './automation-card'
export { AutomationStatusBadge } from './automation-status-badge'
export { ExecutionTimeline } from './execution-timeline'
export { ExecutionLogsViewer } from './execution-logs-viewer'
export { ValidationCard, ValidationList } from './validation-card'
export { AutomationDetailSheet } from './automation-detail-sheet'  // Nouveau
```

## Dépendances entre fichiers

```
automation-detail-sheet.tsx
├── Utilise automation-status-badge.tsx
├── Utilise execution-timeline.tsx
├── Utilise execution-logs-viewer.tsx
├── Utilise validation-card.tsx (ValidationList)
├── Importe @/services/automations/automations.hooks
│   ├── useAutomation
│   └── useAutomationExecutions
└── Importe @/lib/mock-data/automations-mock
    ├── getLogsByExecutionId
    └── getValidationsByAutomationId
```

## Services et données

### Hooks React Query
**Fichier:** `/src/services/automations/automations.hooks.ts`

```typescript
useAutomation(id: string)
useAutomationExecutions(automationId: string)
useExecutionLogs(executionId: string)  // Pas encore utilisé (données mockées)
```

### Données mockées
**Fichier:** `/src/lib/mock-data/automations-mock.ts`

```typescript
mockAutomations: Automation[]
mockExecutions: Execution[]
mockExecutionLogs: ExecutionLog[]
mockValidations: AutomationValidation[]

// Helpers
getExecutionsByAutomationId(automationId: string)
getLogsByExecutionId(executionId: string)
getValidationsByAutomationId(automationId: string)
```

## Types TypeScript

**Fichier:** `/src/services/automations/automations.types.ts`

```typescript
interface Automation {
  id: string
  user_id: string
  name: string
  description: string | null
  status: 'draft' | 'active' | 'paused' | 'archived'
  enabled: boolean
  permission_level: string
  is_system: boolean
  tags: string[]
  created_at: string
  updated_at: string
}

interface Execution {
  id: string
  automation_id: string
  status: 'pending' | 'running' | 'success' | 'failed'
  started_at: string
  completed_at: string | null
  params: Record<string, any>
  result: any
  error_message: string | null
}

interface ExecutionLog {
  id: string
  execution_id: string
  step_order: number
  step_name: string
  level: 'INFO' | 'WARNING' | 'ERROR'
  message: string
  timestamp: string
  metadata: Record<string, any> | null
}

interface AutomationValidation {
  id: string
  automation_id: string
  execution_id: string
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
  validated_at: string | null
  feedback: string | null
}
```

## Comment utiliser ce module

### 1. Import du composant principal

```tsx
import { AutomationDetailSheet } from '@/components/automations'
```

### 2. Utilisation dans une page

Voir `INTEGRATION_EXAMPLE.tsx` pour des exemples complets

### 3. Tester avec la démo

```tsx
import { AutomationDetailSheetDemo } from '@/components/automations/automation-detail-sheet.demo'

<AutomationDetailSheetDemo />
```

### 4. IDs mockés disponibles

- `auto_001` - Génération de rapports hebdomadaires
- `auto_002` - Backup quotidien des données
- `auto_003` - Synchronisation des utilisateurs

## Composants UI utilisés (Shadcn)

- Sheet
- Tabs
- Badge
- Skeleton
- Select
- Timeline (custom)
- Accordion
- Input
- ScrollArea

## Librairies externes

- `date-fns` + `date-fns/locale` - Formatage des dates
- `lucide-react` - Icônes
- `@tanstack/react-query` - Gestion des données

## Prochaines évolutions

1. Remplacer `getLogsByExecutionId` par `useExecutionLogs` quand backend sera prêt
2. Ajouter des actions sur l'onglet Infos (edit, toggle, etc.)
3. Implémenter les validations en mode éditable (actuellement READ-ONLY)
4. Ajouter un onglet "Configuration" si besoin
