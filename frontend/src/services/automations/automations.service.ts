import { apiClient } from '@/lib/api-client'
import type { Automation, Execution, ExecutionLog, WorkflowStep } from './automations.types'
import { mockAutomations, getExecutionsByAutomationId, mockExecutionLogs } from '@/lib/mock-data/automations-mock'

// Query keys
export const automationKeys = {
  all: ['automations'] as const,
  lists: () => [...automationKeys.all, 'list'] as const,
  detail: (id: string) => [...automationKeys.all, 'detail', id] as const,
  executions: (id: string) => [...automationKeys.all, id, 'executions'] as const,
  executionLogs: (executionId: string) => ['executions', executionId, 'logs'] as const,
  workflowSteps: (id: string) => [...automationKeys.all, id, 'workflow-steps'] as const,
}

// Service
export const automationService = {
  async getAll(): Promise<Automation[]> {
    // API RÉELLE
    const { data } = await apiClient.get('/automations')
    return data
  },

  async getById(id: string): Promise<Automation> {
    // API RÉELLE
    const { data } = await apiClient.get(`/automations/${id}`)
    return data
  },

  async getExecutions(automationId: string): Promise<Execution[]> {
    // API RÉELLE
    const { data } = await apiClient.get(`/automations/${automationId}/executions`)
    return data
  },

  async getExecutionLogs(executionId: string): Promise<ExecutionLog[]> {
    // API RÉELLE
    const { data } = await apiClient.get(`/automations/executions/${executionId}/logs`)
    return data
  },

  async getWorkflowSteps(automationId: string): Promise<WorkflowStep[]> {
    // API RÉELLE
    const { data } = await apiClient.get(`/automations/${automationId}/steps`)
    return data
  },

  async toggleEnabled(id: string, enabled: boolean): Promise<Automation> {
    // API RÉELLE
    const { data } = await apiClient.patch(`/automations/${id}`, { enabled })
    return data
  },

  async delete(id: string, headers?: Record<string, string>): Promise<void> {
    // API RÉELLE - Support cascade delete avec header de confirmation
    await apiClient.delete(`/automations/${id}`, { headers })
  },
}
