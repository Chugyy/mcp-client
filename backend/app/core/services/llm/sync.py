# app/core/services/llm/sync.py
"""Service de synchronisation des modèles LLM depuis les providers vers la DB."""

from typing import Dict, List, Any
from config.logger import logger
from app.core.services.llm.gateway import llm_gateway
from app.database import crud

# Mapping des noms de providers API vers les noms de services en DB
PROVIDER_NAME_MAPPING = {
    "openai": "OpenAI",
    "anthropic": "Anthropic"
}


class ModelSyncService:
    """Service pour synchroniser les modèles depuis les providers vers la BDD."""

    async def fetch_models_from_providers(self, provider: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Récupère la liste des modèles depuis les APIs des providers.

        Args:
            provider: Provider spécifique ou None pour tous

        Returns:
            Dict avec les modèles groupés par provider
        """
        try:
            models = await llm_gateway.list_models(provider=provider)
            return models
        except Exception as e:
            logger.error(f"Error fetching models from providers: {e}")
            raise

    async def sync_models_to_db(self, provider: str = None) -> Dict[str, Any]:
        """
        Synchronise les modèles depuis les providers vers la base de données.

        Args:
            provider: Provider spécifique ou None pour tous

        Returns:
            Dict avec le rapport de synchronisation:
            {
                "created": [...],
                "already_exists": [...],
                "errors": [...]
            }
        """
        report = {
            "created": [],
            "already_exists": [],
            "errors": []
        }

        try:
            # Récupérer les modèles depuis les providers
            provider_models = await self.fetch_models_from_providers(provider)

            if not provider_models:
                logger.warning("No models fetched from providers")
                return report

            # Pour chaque provider
            for provider_name, models in provider_models.items():
                logger.info(f"Processing {len(models)} models from {provider_name}")

                # Récupérer le nom correct du service depuis le mapping
                service_name = PROVIDER_NAME_MAPPING.get(provider_name, provider_name.capitalize())

                # Vérifier si le service existe en BDD
                service = await crud.get_service_by_name_and_provider(
                    name=service_name,
                    provider=provider_name
                )

                if not service:
                    # Créer le service s'il n'existe pas
                    logger.info(f"Creating service for provider {provider_name}")
                    try:
                        service_id = await crud.create_service(
                            name=service_name,
                            provider=provider_name,
                            description=f"{service_name} API",
                            status="active"
                        )
                        service = await crud.get_service(service_id)
                    except Exception as e:
                        logger.error(f"Failed to create service for {provider_name}: {e}")
                        report["errors"].append({
                            "provider": provider_name,
                            "error": str(e)
                        })
                        continue

                service_id = service['id']

                # Synchroniser chaque modèle
                for model_data in models:
                    model_name = model_data.get('id') or model_data.get('model')

                    if not model_name:
                        logger.warning(f"Model without id/model field: {model_data}")
                        continue

                    # Récupérer le display_name depuis l'API (généré par les adapters)
                    display_name = model_data.get('display_name') or model_name

                    try:
                        # Vérifier si le modèle existe déjà
                        existing_model = await crud.get_model_by_name(service_id, model_name)

                        if existing_model:
                            report["already_exists"].append({
                                "service": provider_name,
                                "model_name": model_name
                            })
                            logger.debug(f"Model {model_name} already exists")
                        else:
                            # Créer le modèle avec le vrai display_name
                            model_id = await crud.create_model(
                                service_id=service_id,
                                model_name=model_name,
                                display_name=display_name,
                                description=f"Model {model_name} from {provider_name}",
                                enabled=True
                            )
                            report["created"].append({
                                "id": model_id,
                                "service": provider_name,
                                "model_name": model_name,
                                "display_name": display_name
                            })
                            logger.info(f"✅ Created model {model_name} (display: {display_name})")

                    except Exception as e:
                        logger.error(f"Failed to sync model {model_name}: {e}")
                        report["errors"].append({
                            "service": provider_name,
                            "model_name": model_name,
                            "error": str(e)
                        })

            logger.info(f"Sync completed: {len(report['created'])} created, "
                       f"{len(report['already_exists'])} already exists, "
                       f"{len(report['errors'])} errors")

            return report

        except Exception as e:
            logger.error(f"Error during model sync: {e}")
            raise


# Instance globale réutilisable
model_sync_service = ModelSyncService()


async def daily_model_sync_job():
    """
    Job quotidien de synchronisation des modèles.
    Appelé par le scheduler tous les jours à 00h.
    """
    logger.info("🔄 Starting daily model sync job...")
    try:
        report = await model_sync_service.sync_models_to_db()
        logger.info(f"✅ Daily sync completed: {len(report['created'])} created, "
                   f"{len(report['already_exists'])} already exists, "
                   f"{len(report['errors'])} errors")
    except Exception as e:
        logger.error(f"❌ Daily sync job failed: {e}")
