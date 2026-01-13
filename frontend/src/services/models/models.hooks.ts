import { useQuery } from '@tanstack/react-query'
import { modelsService, modelKeys } from './models.service'

/**
 * Hook pour récupérer tous les modèles disponibles pour l'utilisateur
 */
export function useModels() {
  return useQuery({
    queryKey: modelKeys.lists(),
    queryFn: modelsService.getAll,
  })
}

/**
 * Hook pour récupérer tous les modèles avec informations de service
 */
export function useModelsWithService() {
  return useQuery({
    queryKey: modelKeys.listsWithService(),
    queryFn: modelsService.getAllWithService,
  })
}

/**
 * Hook pour récupérer un modèle par ID
 */
export function useModel(id: string) {
  return useQuery({
    queryKey: modelKeys.detail(id),
    queryFn: () => modelsService.getById(id),
    enabled: !!id,
  })
}
