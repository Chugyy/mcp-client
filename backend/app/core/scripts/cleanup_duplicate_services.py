#!/usr/bin/env python3
"""
Script de nettoyage pour supprimer les services LLM en double/test.
Ne garde que les vrais services OpenAI et Anthropic.
"""

import asyncio
from app.database import crud
from config.logger import logger


async def cleanup_services():
    """Supprime les services en double et les services de test."""

    # Récupérer tous les services
    all_services = await crud.list_services()
    logger.info(f"📊 Total de services trouvés: {len(all_services)}")

    # Services à conserver (noms exacts)
    services_to_keep = ["OpenAI", "Anthropic"]

    # Parcourir et supprimer les services indésirables
    deleted_count = 0
    kept_services = []

    for service in all_services:
        service_name = service['name']
        service_id = service['id']
        service_provider = service['provider']
        service_desc = service.get('description', '')

        # Critères de suppression :
        # 1. Nom contient "Test" ou "test"
        # 2. Description contient "test"
        # 3. Nom n'est pas dans la liste des services à garder
        # 4. Doublons (si on a déjà un service avec le même provider)

        should_delete = False
        reason = ""

        if "test" in service_name.lower() or "test" in service_desc.lower():
            should_delete = True
            reason = "Service de test"
        elif service_name not in services_to_keep:
            # Vérifier si c'est un doublon (ex: "Openai" vs "OpenAI")
            if service_provider in ['openai', 'anthropic']:
                # Garder uniquement si le nom est exact
                if service_name not in services_to_keep:
                    should_delete = True
                    reason = f"Doublon ou mauvais format (nom: {service_name})"
            else:
                # Provider non-LLM (mcp, resource, etc.)
                should_delete = True
                reason = f"Provider non-LLM ({service_provider})"

        if should_delete:
            logger.info(f"🗑️  Suppression: {service_name} (ID: {service_id}) - Raison: {reason}")
            try:
                await crud.delete_service(service_id)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Erreur lors de la suppression de {service_name}: {e}")
        else:
            logger.info(f"✓ Conservé: {service_name} ({service_provider})")
            kept_services.append(service)

    logger.info(f"\n📊 Résumé:")
    logger.info(f"  - Services supprimés: {deleted_count}")
    logger.info(f"  - Services conservés: {len(kept_services)}")

    if kept_services:
        logger.info(f"\n✓ Services finaux:")
        for s in kept_services:
            logger.info(f"  - {s['name']} ({s['provider']}) - {s['description']}")


async def main():
    logger.info("🧹 Nettoyage des services en double...")
    await cleanup_services()
    logger.info("\n✓ Nettoyage terminé")


if __name__ == "__main__":
    asyncio.run(main())
