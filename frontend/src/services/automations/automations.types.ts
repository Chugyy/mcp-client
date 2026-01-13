// Automation principale
export interface Automation {
  id: string
  user_id: string
  name: string
  description: string | null
  enabled: boolean
  is_system: boolean
  created_at: string
  updated_at: string
  // Enrichissement pour la card
  last_execution?: LastExecution
  triggers?: Trigger[]
  health_status?: 'healthy' | 'warning' | 'error'
  health_issues?: string[]
  stats?: AutomationStats
}

// Dernière exécution (pour la card)
export interface LastExecution {
  id: string
  status: 'running' | 'success' | 'failed' | 'cancelled'
  started_at: string
  completed_at: string | null
  duration_ms?: number
}

// Statistiques (pour la card)
export interface AutomationStats {
  total_executions: number
  success_count: number
  failed_count: number
  success_rate: number
}

// Execution complète
export interface Execution {
  id: string
  automation_id: string
  trigger_id: string | null
  user_id: string
  status: 'running' | 'success' | 'failed' | 'cancelled'
  input_params: Record<string, any>
  result: any
  error: string | null
  error_step_id: string | null
  started_at: string
  completed_at: string | null
  paused_at: string | null
}

// Logs d'execution (aligné backend)
export interface ExecutionLog {
  id: string
  execution_id: string
  step_id: string
  step_order: number
  step_name: string
  step_type: 'action' | 'control'
  step_subtype: string
  status: 'running' | 'success' | 'failed' | 'skipped'
  result: any
  error: string | null
  duration_ms: number
  executed_at: string
}

// Workflow Step
export interface WorkflowStep {
  id: string
  automation_id: string
  step_order: number
  step_name: string
  step_type: 'action' | 'control'
  step_subtype: string
  config: Record<string, any>
  run_condition: string | null
  enabled: boolean
  created_at: string
}

// Trigger
export interface Trigger {
  id: string
  automation_id: string
  trigger_type: 'cron' | 'webhook' | 'date' | 'event' | 'manual'
  config: Record<string, any>
  enabled: boolean
  created_at: string
}
