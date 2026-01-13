#!/usr/bin/env python3
"""
Script de seed pour créer les services LLM de base (OpenAI, Anthropic).
À exécuter une seule fois après la création de la base de données.
"""

import asyncio
from app.database import crud
from config.logger import logger


async def seed_llm_services():
    """Crée les services LLM de base s'ils n'existent pas déjà."""

    services_to_create = [
        {
            "name": "OpenAI",
            "provider": "openai",
            "description": "OpenAI API - GPT-4, GPT-4o, GPT-3.5",
            "status": "active"
        },
        {
            "name": "Anthropic",
            "provider": "anthropic",
            "description": "Anthropic API - Claude 3.5 Sonnet, Claude 3 Opus",
            "status": "active"
        }
    ]

    for service_data in services_to_create:
        try:
            # Vérifier si le service existe déjà
            existing = await crud.get_service_by_name_and_provider(
                service_data["name"],
                service_data["provider"]
            )

            if existing:
                logger.info(f"Service {service_data['name']} ({service_data['provider']}) existe déjà")
                continue

            # Créer le service
            service_id = await crud.create_service(
                name=service_data["name"],
                provider=service_data["provider"],
                description=service_data["description"],
                status=service_data["status"]
            )

            logger.info(f"✓ Service créé: {service_data['name']} (ID: {service_id})")

        except Exception as e:
            logger.error(f"Erreur lors de la création du service {service_data['name']}: {e}")


async def main():
    logger.info("🌱 Seed des services LLM...")
    await seed_llm_services()
    logger.info("✓ Seed terminé")


if __name__ == "__main__":
    asyncio.run(main())
