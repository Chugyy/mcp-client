// Types
export type {
  Automation,
  Execution,
  ExecutionLog,
  AutomationValidation,
} from './automations.types'

// Service
export { automationService, automationKeys } from './automations.service'

// Hooks
export {
  useAutomations,
  useAutomation,
  useAutomationExecutions,
  useExecutionLogs,
  useToggleAutomation,
} from './automations.hooks'

// Validations (placeholder)
export { validationService } from './validations.service'
