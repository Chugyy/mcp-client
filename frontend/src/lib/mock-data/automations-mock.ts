/**
 * ⚠️ DONNÉES MOCKÉES - TEMPORAIRE
 *
 * Ce fichier contient des données mockées pour les automations, validations et logs.
 * Ces données seront remplacées par les vrais appels API une fois les endpoints backend implémentés.
 *
 * ENDPOINTS EN ATTENTE :
 * - GET /automations/{id}/validations
 * - POST /automations/{id}/validations
 * - PATCH /validations/{id}
 *
 * TODO: Supprimer ce fichier et migrer vers les services réels dans :
 * - src/services/automations/validations.service.ts
 * - src/services/automations/logs.service.ts (si nécessaire)
 *
 * Date de création : 2025-12-03
 * À supprimer après implémentation backend
 */

import type { Automation, Execution, ExecutionLog, AutomationValidation } from '@/services/automations/automations.types'

// ===== AUTOMATIONS MOCKÉES =====
export const mockAutomations: Automation[] = [
  {
    id: 'auto_001',
    user_id: 'user_123',
    name: 'Génération de rapports hebdomadaires',
    description: 'Génère automatiquement les rapports hebdomadaires et les envoie par email',
    status: 'active',
    enabled: true,
    permission_level: 'read_write',
    is_system: false,
    tags: ['reporting', 'email', 'hebdomadaire'],
    created_at: '2025-11-15T10:00:00Z',
    updated_at: '2025-12-01T14:30:00Z',
  },
  {
    id: 'auto_002',
    user_id: 'user_123',
    name: 'Backup quotidien des données',
    description: 'Sauvegarde automatique des données chaque nuit à 2h00',
    status: 'paused',
    enabled: false,
    permission_level: 'admin',
    is_system: false,
    tags: ['backup', 'maintenance'],
    created_at: '2025-10-20T08:15:00Z',
    updated_at: '2025-11-28T09:45:00Z',
  },
  {
    id: 'auto_003',
    user_id: 'user_123',
    name: 'Synchronisation des utilisateurs',
    description: 'Synchronise les utilisateurs avec le système externe',
    status: 'archived',
    enabled: false,
    permission_level: 'read_only',
    is_system: true,
    tags: ['sync', 'users', 'system'],
    created_at: '2025-09-10T12:00:00Z',
    updated_at: '2025-10-05T16:20:00Z',
  },
]

// ===== EXECUTIONS MOCKÉES =====
export const mockExecutions: Execution[] = [
  // Executions pour auto_001
  {
    id: 'exec_001',
    automation_id: 'auto_001',
    status: 'success',
    started_at: '2025-12-01T09:00:00Z',
    completed_at: '2025-12-01T09:05:23Z',
    params: { report_type: 'weekly', send_email: true },
    result: { report_id: 'report_123', emails_sent: 15 },
    error_message: null,
  },
  {
    id: 'exec_002',
    automation_id: 'auto_001',
    status: 'success',
    started_at: '2025-11-24T09:00:00Z',
    completed_at: '2025-11-24T09:04:12Z',
    params: { report_type: 'weekly', send_email: true },
    result: { report_id: 'report_122', emails_sent: 14 },
    error_message: null,
  },
  {
    id: 'exec_003',
    automation_id: 'auto_001',
    status: 'running',
    started_at: '2025-12-03T09:00:00Z',
    completed_at: null,
    params: { report_type: 'weekly', send_email: true },
    result: null,
    error_message: null,
  },
  // Executions pour auto_002
  {
    id: 'exec_004',
    automation_id: 'auto_002',
    status: 'failed',
    started_at: '2025-11-27T02:00:00Z',
    completed_at: '2025-11-27T02:01:45Z',
    params: { backup_type: 'full' },
    result: null,
    error_message: 'Disk space insufficient',
  },
  {
    id: 'exec_005',
    automation_id: 'auto_002',
    status: 'success',
    started_at: '2025-11-26T02:00:00Z',
    completed_at: '2025-11-26T02:15:30Z',
    params: { backup_type: 'full' },
    result: { backup_size: '2.5GB', files_backed_up: 12543 },
    error_message: null,
  },
  {
    id: 'exec_006',
    automation_id: 'auto_002',
    status: 'pending',
    started_at: '2025-12-03T02:00:00Z',
    completed_at: null,
    params: { backup_type: 'full' },
    result: null,
    error_message: null,
  },
  // Executions pour auto_003
  {
    id: 'exec_007',
    automation_id: 'auto_003',
    status: 'success',
    started_at: '2025-10-05T12:00:00Z',
    completed_at: '2025-10-05T12:10:00Z',
    params: { sync_type: 'incremental' },
    result: { users_synced: 245 },
    error_message: null,
  },
  {
    id: 'exec_008',
    automation_id: 'auto_003',
    status: 'success',
    started_at: '2025-10-04T12:00:00Z',
    completed_at: '2025-10-04T12:08:15Z',
    params: { sync_type: 'incremental' },
    result: { users_synced: 198 },
    error_message: null,
  },
  {
    id: 'exec_009',
    automation_id: 'auto_001',
    status: 'failed',
    started_at: '2025-11-17T09:00:00Z',
    completed_at: '2025-11-17T09:02:30Z',
    params: { report_type: 'weekly', send_email: true },
    result: null,
    error_message: 'SMTP server unreachable',
  },
  {
    id: 'exec_010',
    automation_id: 'auto_001',
    status: 'pending',
    started_at: '2025-12-03T10:00:00Z',
    completed_at: null,
    params: { report_type: 'daily', send_email: false },
    result: null,
    error_message: null,
  },
]

// ===== LOGS MOCKÉS =====
export const mockExecutionLogs: ExecutionLog[] = [
  // Logs pour exec_001
  {
    id: 'log_001',
    execution_id: 'exec_001',
    step_order: 1,
    step_name: 'Initialisation',
    level: 'INFO',
    message: 'Démarrage de la génération du rapport',
    timestamp: '2025-12-01T09:00:00Z',
    metadata: { step_duration_ms: 120 },
  },
  {
    id: 'log_002',
    execution_id: 'exec_001',
    step_order: 2,
    step_name: 'Collecte des données',
    level: 'INFO',
    message: 'Collecte des données depuis la base',
    timestamp: '2025-12-01T09:00:30Z',
    metadata: { rows_fetched: 1523 },
  },
  {
    id: 'log_003',
    execution_id: 'exec_001',
    step_order: 3,
    step_name: 'Génération du rapport',
    level: 'INFO',
    message: 'Génération du fichier PDF',
    timestamp: '2025-12-01T09:02:00Z',
    metadata: { pdf_size_kb: 245 },
  },
  {
    id: 'log_004',
    execution_id: 'exec_001',
    step_order: 4,
    step_name: 'Envoi des emails',
    level: 'INFO',
    message: 'Envoi des emails aux destinataires',
    timestamp: '2025-12-01T09:04:00Z',
    metadata: { emails_sent: 15, emails_failed: 0 },
  },
  {
    id: 'log_005',
    execution_id: 'exec_001',
    step_order: 5,
    step_name: 'Finalisation',
    level: 'INFO',
    message: 'Rapport généré et envoyé avec succès',
    timestamp: '2025-12-01T09:05:23Z',
    metadata: null,
  },
  // Logs pour exec_004 (failed)
  {
    id: 'log_006',
    execution_id: 'exec_004',
    step_order: 1,
    step_name: 'Vérification espace disque',
    level: 'WARNING',
    message: 'Espace disque faible détecté',
    timestamp: '2025-11-27T02:00:00Z',
    metadata: { available_space_gb: 2.3, required_space_gb: 5.0 },
  },
  {
    id: 'log_007',
    execution_id: 'exec_004',
    step_order: 2,
    step_name: 'Tentative de backup',
    level: 'ERROR',
    message: 'Échec du backup: espace disque insuffisant',
    timestamp: '2025-11-27T02:01:45Z',
    metadata: { error_code: 'DISK_FULL' },
  },
  // Logs pour exec_003 (running)
  {
    id: 'log_008',
    execution_id: 'exec_003',
    step_order: 1,
    step_name: 'Initialisation',
    level: 'INFO',
    message: 'Démarrage de la génération du rapport',
    timestamp: '2025-12-03T09:00:00Z',
    metadata: null,
  },
  {
    id: 'log_009',
    execution_id: 'exec_003',
    step_order: 2,
    step_name: 'Collecte des données',
    level: 'INFO',
    message: 'Collecte en cours...',
    timestamp: '2025-12-03T09:00:30Z',
    metadata: { progress: 45 },
  },
  // Logs additionnels pour exec_002
  {
    id: 'log_010',
    execution_id: 'exec_002',
    step_order: 1,
    step_name: 'Initialisation',
    level: 'INFO',
    message: 'Démarrage de la génération du rapport',
    timestamp: '2025-11-24T09:00:00Z',
    metadata: null,
  },
  {
    id: 'log_011',
    execution_id: 'exec_002',
    step_order: 2,
    step_name: 'Collecte des données',
    level: 'INFO',
    message: 'Collecte des données depuis la base',
    timestamp: '2025-11-24T09:00:20Z',
    metadata: { rows_fetched: 1398 },
  },
  {
    id: 'log_012',
    execution_id: 'exec_002',
    step_order: 3,
    step_name: 'Génération du rapport',
    level: 'WARNING',
    message: 'Certaines données manquantes, utilisation des valeurs par défaut',
    timestamp: '2025-11-24T09:02:10Z',
    metadata: { missing_fields: ['region', 'category'] },
  },
  {
    id: 'log_013',
    execution_id: 'exec_002',
    step_order: 4,
    step_name: 'Envoi des emails',
    level: 'INFO',
    message: 'Envoi des emails aux destinataires',
    timestamp: '2025-11-24T09:03:30Z',
    metadata: { emails_sent: 14, emails_failed: 0 },
  },
  {
    id: 'log_014',
    execution_id: 'exec_002',
    step_order: 5,
    step_name: 'Finalisation',
    level: 'INFO',
    message: 'Rapport généré et envoyé avec succès',
    timestamp: '2025-11-24T09:04:12Z',
    metadata: null,
  },
  // Logs pour exec_009 (failed)
  {
    id: 'log_015',
    execution_id: 'exec_009',
    step_order: 1,
    step_name: 'Initialisation',
    level: 'INFO',
    message: 'Démarrage de la génération du rapport',
    timestamp: '2025-11-17T09:00:00Z',
    metadata: null,
  },
  {
    id: 'log_016',
    execution_id: 'exec_009',
    step_order: 2,
    step_name: 'Collecte des données',
    level: 'INFO',
    message: 'Collecte des données depuis la base',
    timestamp: '2025-11-17T09:00:15Z',
    metadata: { rows_fetched: 1612 },
  },
  {
    id: 'log_017',
    execution_id: 'exec_009',
    step_order: 3,
    step_name: 'Génération du rapport',
    level: 'INFO',
    message: 'Génération du fichier PDF',
    timestamp: '2025-11-17T09:01:30Z',
    metadata: { pdf_size_kb: 289 },
  },
  {
    id: 'log_018',
    execution_id: 'exec_009',
    step_order: 4,
    step_name: 'Envoi des emails',
    level: 'ERROR',
    message: 'Impossible de se connecter au serveur SMTP',
    timestamp: '2025-11-17T09:02:30Z',
    metadata: { smtp_host: 'smtp.example.com', error_code: 'CONNECTION_REFUSED' },
  },
  // Logs pour exec_005
  {
    id: 'log_019',
    execution_id: 'exec_005',
    step_order: 1,
    step_name: 'Initialisation du backup',
    level: 'INFO',
    message: 'Démarrage du backup complet',
    timestamp: '2025-11-26T02:00:00Z',
    metadata: { backup_type: 'full' },
  },
  {
    id: 'log_020',
    execution_id: 'exec_005',
    step_order: 2,
    step_name: 'Backup des fichiers',
    level: 'INFO',
    message: 'Backup terminé avec succès',
    timestamp: '2025-11-26T02:15:30Z',
    metadata: { backup_size: '2.5GB', files_backed_up: 12543, duration_minutes: 15.5 },
  },
]

// ===== VALIDATIONS MOCKÉES =====
export const mockValidations: AutomationValidation[] = [
  {
    id: 'val_001',
    automation_id: 'auto_001',
    execution_id: 'exec_001',
    status: 'approved',
    created_at: '2025-12-01T09:05:30Z',
    validated_at: '2025-12-01T09:10:15Z',
    feedback: null,
  },
  {
    id: 'val_002',
    automation_id: 'auto_001',
    execution_id: 'exec_003',
    status: 'pending',
    created_at: '2025-12-03T09:00:30Z',
    validated_at: null,
    feedback: null,
  },
  {
    id: 'val_003',
    automation_id: 'auto_002',
    execution_id: 'exec_004',
    status: 'rejected',
    created_at: '2025-11-27T02:02:00Z',
    validated_at: '2025-11-27T08:30:00Z',
    feedback: 'Backup échoué en raison d\'un manque d\'espace disque. Augmenter la capacité avant de relancer.',
  },
  {
    id: 'val_004',
    automation_id: 'auto_002',
    execution_id: 'exec_005',
    status: 'approved',
    created_at: '2025-11-26T02:16:00Z',
    validated_at: '2025-11-26T08:00:00Z',
    feedback: null,
  },
  {
    id: 'val_005',
    automation_id: 'auto_001',
    execution_id: 'exec_009',
    status: 'pending',
    created_at: '2025-11-17T09:03:00Z',
    validated_at: null,
    feedback: null,
  },
  {
    id: 'val_006',
    automation_id: 'auto_001',
    execution_id: 'exec_002',
    status: 'approved',
    created_at: '2025-11-24T09:04:30Z',
    validated_at: '2025-11-24T09:15:20Z',
    feedback: 'Rapport bien généré avec toutes les données attendues',
  },
  {
    id: 'val_007',
    automation_id: 'auto_001',
    execution_id: 'exec_010',
    status: 'pending',
    created_at: '2025-12-03T10:00:30Z',
    validated_at: null,
    feedback: null,
  },
]

// ===== FONCTIONS HELPER POUR FILTRER LES DONNÉES =====

export function getExecutionsByAutomationId(automationId: string): Execution[] {
  return mockExecutions.filter(exec => exec.automation_id === automationId)
}

export function getLogsByExecutionId(executionId: string): ExecutionLog[] {
  return mockExecutionLogs.filter(log => log.execution_id === executionId)
}

export function getValidationsByAutomationId(automationId: string): AutomationValidation[] {
  return mockValidations.filter(val => val.automation_id === automationId)
}
