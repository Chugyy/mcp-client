/**
 * ============================================================================
 * ⚠️ ATTENTION - DISAMBIGUATION
 * ============================================================================
 *
 * Ce fichier concerne les VALIDATIONS DES AUTOMATIONS (fonctionnalité future).
 *
 * Si vous cherchez le système de validations de TOOL CALLS (approve/reject/feedback),
 * utilisez plutôt :
 *
 * ➡️  services/validations/validations.hooks.ts
 * ➡️  services/validations/validations.service.ts
 * ➡️  services/validations/validations.types.ts
 *
 * Les deux systèmes sont différents :
 * - services/validations/        → Validations des tool calls MCP (IMPLÉMENTÉ)
 * - services/automations/validations.service.ts → Validations des automations (TODO)
 *
 * ============================================================================
 */

/**
 * TODO: Service Validations des Automations
 *
 * Ce fichier est prévu pour gérer les validations des automations.
 * Actuellement, les données de validations sont mockées dans @/lib/mock-data/automations-mock.ts
 *
 * ENDPOINTS BACKEND À IMPLÉMENTER :
 * - GET /automations/{id}/validations - Liste des validations d'une automation
 * - POST /automations/{id}/validations - Créer une validation
 * - PATCH /validations/{id} - Mettre à jour une validation (approuver/rejeter)
 *
 * TYPES À CRÉER :
 * - AutomationValidation (déjà dans automations.types.ts)
 * - ValidationCreate (DTO pour création)
 * - ValidationUpdate (DTO pour mise à jour)
 *
 * FONCTIONS À IMPLÉMENTER :
 * - getValidations(automationId: string): Promise<AutomationValidation[]>
 * - createValidation(automationId: string, dto: ValidationCreate): Promise<AutomationValidation>
 * - updateValidation(id: string, dto: ValidationUpdate): Promise<AutomationValidation>
 *
 * QUERY KEYS :
 * - validations: (automationId: string) => [...automationKeys.all, automationId, 'validations']
 *
 * HOOKS À CRÉER :
 * - useAutomationValidations(automationId: string)
 * - useCreateValidation()
 * - useUpdateValidation()
 */

// Placeholder pour éviter les erreurs d'import
export const validationService = {}
