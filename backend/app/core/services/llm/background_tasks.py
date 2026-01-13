# app/core/services/llm/background_tasks.py
"""
Background tasks pour la génération LLM.

Ce module contient les tâches asynchrones qui s'exécutent sans stream frontend actif,
notamment la continuation de génération après validation depuis la page /validation.
"""

import asyncio
from datetime import datetime
from typing import Any
from app.database import crud
from app.database.models import User, Chat, Agent
from app.core.services.llm.manager import StreamSession
from config.logger import logger


async def resume_generation_after_validation(
    chat_id: str,
    validation_id: str,
    tool_result: Any,
    user: User
):
    """
    Continue la génération LLM après validation, SANS stream frontend actif.
    Sauvegarde directement les résultats en DB.

    Args:
        chat_id: ID du chat
        validation_id: ID de la validation approuvée
        tool_result: Résultat de l'exécution du tool
        user: Utilisateur authentifié

    Side effects:
        - Marque chat.is_generating = True
        - Crée messages assistant en DB
        - Marque chat.is_generating = False à la fin
        - Peut créer de nouvelles validations si nécessaire

    Note:
        Cette fonction s'exécute en arrière-plan (asyncio.create_task)
        sans connexion frontend active.
    """
    from app.database.crud import chats as crud_chats

    try:
        # 1. Marquer le chat comme "en génération"
        await crud_chats.update_chat_generating_status(chat_id, is_generating=True)

        logger.info(f"🔄 Background generation started for chat {chat_id}")

        # 2. Récupérer le contexte du chat
        chat = await crud.get_chat(chat_id)
        if not chat:
            logger.error(f"Chat {chat_id} not found")
            return

        chat_obj = Chat.from_row(chat)

        # 3. Récupérer l'agent et les messages
        if not chat_obj.agent_id:
            logger.error(f"Chat {chat_id} has no agent")
            return

        agent = await crud.get_agent(chat_obj.agent_id)
        if not agent:
            logger.error(f"Agent {chat_obj.agent_id} not found")
            return

        agent_obj = Agent.from_row(agent)

        history = await crud.get_messages_by_chat(chat_id, limit=100)
        messages = [
            {"role": msg['role'], "content": msg['content']}
            for msg in history
            if msg['role'] in ('user', 'assistant')
        ]

        # 4. Construire le contexte
        from app.core.services.contextualizer import contextualizer
        context_data = await contextualizer.build_context(
            chat_id=chat_id,
            agent_id=chat_obj.agent_id,
            team_id=chat_obj.team_id
        )
        tools_for_llm = contextualizer.get_tools_for_llm(context_data)

        if not tools_for_llm:
            logger.warning(f"No tools available for chat {chat_id}, cannot continue")
            return

        # 5. Créer une session background (sans stream frontend)
        background_session = StreamSession(
            chat_id=chat_id,
            user_id=user.id,
            started_at=datetime.now()
        )

        # Injecter immédiatement le résultat de validation
        background_session.validation_result = {
            "validation_id": validation_id,
            "action": "approved",
            "data": tool_result
        }
        background_session.validation_event.set()

        # 6. Appeler le LLM (sans yield, juste accumuler)
        from app.core.services.llm.gateway import llm_gateway

        full_response = ""

        stream_method = llm_gateway.stream_with_tools(
            messages=messages,
            model=chat_obj.model or "gpt-4o-mini",
            tools=tools_for_llm,
            system_prompt=agent_obj.system_prompt,
            api_key_id=None,
            chat_id=chat_id,
            user=user,
            agent_id=chat_obj.agent_id,
            session=background_session,
            context_data=context_data
        )

        # 7. Consommer le stream SANS le yield (on accumule juste)
        async for chunk in stream_method:
            # Ignorer les events spéciaux
            if chunk.startswith("["):
                if chunk.startswith("[VALIDATION_REQUIRED:"):
                    # Nouvelle validation requise
                    new_validation_id = chunk[21:-1]
                    logger.info(f"New validation {new_validation_id} required during background generation")
                    # La validation sera créée automatiquement
                    # Arrêter ici, attendre nouvelle validation
                    break
                continue

            # Accumuler le texte
            full_response += chunk

        # 8. Sauvegarder le message final
        if full_response.strip():
            await crud.create_message(
                chat_id=chat_id,
                role="assistant",
                content=full_response,
                metadata=None
            )
            logger.info(f"✅ Background generation completed for chat {chat_id}")

    except Exception as e:
        logger.exception(f"❌ Background generation failed for chat {chat_id}: {e}")

        # Sauvegarder un message d'erreur
        try:
            await crud.create_message(
                chat_id=chat_id,
                role="assistant",
                content=f"Erreur lors de la génération : {str(e)}",
                metadata={"error": True}
            )
        except Exception as save_error:
            logger.error(f"Failed to save error message: {save_error}")

    finally:
        # 9. Démarquer le chat comme "génération terminée"
        try:
            from app.database.crud import chats as crud_chats
            await crud_chats.update_chat_generating_status(chat_id, is_generating=False)
            logger.info(f"🏁 Background generation ended for chat {chat_id}")
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup generation status: {cleanup_error}")
