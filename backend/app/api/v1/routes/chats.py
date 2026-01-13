from fastapi import APIRouter, Depends, status
from app.core.exceptions import ValidationError, NotFoundError, PermissionError, AppException, ConflictError
from fastapi.responses import StreamingResponse
from typing import List, AsyncGenerator
import json
from datetime import datetime
from app.database import crud
from app.database.crud import chats as crud_chats
from app.database.models import User, Chat, Message, Agent, Team
from app.api.v1.schemas import (
    ChatCreate, ChatResponse,
    MessageCreate, MessageResponse,
    ChatRequest,
    MessageStreamRequest
)
from app.core.utils.auth import get_current_user
from app.core.services.llm.chat import chat_service
from app.core.services.llm.manager import StreamSession
from config.logger import logger

router = APIRouter(prefix="/chats", tags=["chats"])

# ============================================================================
# DEPENDENCIES
# ============================================================================

# DEPRECATED: Cette dependency causait une fermeture prématurée de la session
# car le finally se déclenchait avant que le générateur async ne soit consommé.
# La session est maintenant créée directement dans la fonction generate().
#
# async def get_stream_session(
#     chat_id: str,
#     current_user: User = Depends(get_current_user)
# ) -> AsyncGenerator[StreamSession, None]:
#     """
#     Dependency FastAPI pour gérer automatiquement les sessions de streaming.
#     ⚠️ NE PAS UTILISER - Cause une fermeture prématurée !
#     """
#     from app.core.services.llm.manager import stream_manager
#     session = stream_manager.start_session(chat_id, current_user.id)
#     try:
#         yield session
#     finally:
#         stream_manager.end_session(chat_id)  # ❌ Se déclenche trop tôt !


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    request: ChatCreate,
    current_user: User = Depends(get_current_user)
):
    """Crée une nouvelle conversation (vide ou avec agent/team)."""
    # Validation: agent_id XOR team_id (but both can be None for lazy initialization)
    if request.agent_id and request.team_id:
        raise ValidationError("Cannot specify both agent_id and team_id")

    # Vérifier que l'agent ou l'équipe existe (seulement si fourni)
    if request.agent_id:
        agent = await crud.get_agent(request.agent_id)
        if not agent:
            raise NotFoundError("Agent not found")

        agent = Agent.from_row(agent)
        if agent.user_id != current_user.id:
            raise PermissionError("Not authorized to chat with this agent")

    if request.team_id:
        team = await crud.get_team(request.team_id)
        if not team:
            raise NotFoundError("Team not found")

    # Créer le chat (peut être vide si agent_id et team_id sont None)
    chat_id = await crud.create_chat(
        user_id=current_user.id,
        title=request.title,
        agent_id=request.agent_id,
        team_id=request.team_id
    )

    chat = await crud.get_chat(chat_id)
    if not chat:
        raise AppException("Failed to create chat")

    chat = Chat.from_row(chat)
    return ChatResponse(**chat.to_dict())

@router.get("", response_model=List[ChatResponse])
async def list(current_user: User = Depends(get_current_user)):
    """Liste toutes les conversations de l'utilisateur."""
    chats = await crud.list_chats_by_user(current_user.id)
    return [ChatResponse(**Chat.from_row(c).to_dict()) for c in chats]

@router.post("/stream_legacy")
async def stream_legacy(
    data: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """[LEGACY] Stream une réponse chat (text/plain). À supprimer après migration frontend."""

    # Créer ou récupérer chat
    chat_created = False
    if data.chat_id:
        chat = await crud.get_chat(data.chat_id)
        if not chat:
            raise NotFoundError("Chat not found")

        chat = Chat.from_row(chat)
        if chat.user_id != current_user.id:
            raise PermissionError("Not authorized")
    else:
        # Créer un nouveau chat si pas d'ID fourni
        if not data.agent_id:
            raise ValidationError("agent_id required when creating new chat")

        chat_id = await crud.create_chat(
            user_id=current_user.id,
            agent_id=data.agent_id,
            team_id=None,
            title=data.message[:50]
        )
        chat = await crud.get_chat(chat_id)
        chat = Chat.from_row(chat)
        chat_created = True

    # Sauvegarder message user
    await crud.create_message(chat.id, "user", data.message)

    # Récupérer l'agent pour le system_prompt
    system_prompt = "Tu es un assistant utile et bienveillant."
    model = data.model or "gpt-4o-mini"

    if chat.agent_id:
        agent = await crud.get_agent(chat.agent_id)
        if agent:
            agent = Agent.from_row(agent)
            system_prompt = agent.system_prompt
    elif chat.team_id:
        team = await crud.get_team(chat.team_id)
        if team:
            team = Team.from_row(team)
            system_prompt = team.system_prompt

    # === PHASE DE CONSTRUCTION DE CONTEXTE ===
    from app.core.services.contextualizer import contextualizer
    context_data = await contextualizer.build_context(
        chat_id=chat.id,
        agent_id=chat.agent_id,
        team_id=chat.team_id
    )

    # Récupérer les tools depuis le contexte
    tools_for_llm = contextualizer.get_tools_for_llm(context_data)

    # Formater le contexte pour le LLM (ressources uniquement, plus les tools)
    formatted_context = contextualizer.format_context_for_llm(context_data)

    # === INITIALISER LE STREAM MANAGER ===
    from app.core.services.llm.manager import stream_manager

    # Créer ou récupérer une session de streaming
    session = stream_manager.get_session(chat.id)
    if not session:
        session = stream_manager.start_session(
            chat_id=chat.id,
            user_id=current_user.id
        )

    # Reset sources pour ce nouveau message
    session.reset_sources()

    # Stream response
    async def generate():
        full_response = ""
        sources_for_message = []

        try:
            # Utiliser stream_chat_with_tools si des tools sont disponibles
            if tools_for_llm:
                # Appeler directement le gateway avec tous les paramètres nécessaires
                from app.core.services.llm.gateway import llm_gateway

                stream_method = llm_gateway.stream_with_tools(
                    messages=[{"role": "user", "content": data.message}],
                    model=model,
                    tools=tools_for_llm,
                    system_prompt=system_prompt,
                    api_key_id=data.api_key_id,
                    # Nouveaux paramètres pour le système de validation
                    chat_id=chat.id,
                    user=current_user,
                    agent_id=chat.agent_id,
                    session=session,
                    context_data=context_data
                )
            else:
                # Fallback sur le stream classique (sans tools)
                stream_method = chat_service.stream_chat(
                    message=data.message,
                    system_prompt=system_prompt,
                    model=model,
                    api_key_id=data.api_key_id,
                    context=formatted_context if formatted_context else None
                )

            async for chunk in stream_method:
                # Filtrer les events spéciaux pour ne pas les sauvegarder
                if chunk.startswith("[") and chunk.endswith("]"):
                    # Event spécial (VALIDATION_REQUIRED, STOPPED_BY_USER, SOURCES, etc.)
                    if chunk.startswith("[SOURCES:"):
                        # Extraire les sources depuis l'event
                        import json
                        sources_json = chunk[9:-1]  # Enlever "[SOURCES:" et "]"
                        sources_for_message = json.loads(sources_json)
                        logger.debug(f"Received sources: {len(sources_for_message)} resource(s)")

                    yield chunk
                else:
                    # Texte normal
                    full_response += chunk
                    yield chunk

            # Sauvegarder message assistant seulement si pas arrêté
            if not session.stop_event.is_set() and full_response.strip():
                metadata = {}
                if sources_for_message:
                    metadata["sources"] = sources_for_message
                    logger.info(f"Saving message with {len(sources_for_message)} source(s)")

                await crud.create_message(
                    chat.id,
                    "assistant",
                    full_response,
                    metadata=metadata if metadata else None
                )

        finally:
            # Nettoyer la session
            stream_manager.end_session(chat.id)

    headers = {"X-Chat-ID": str(chat.id)} if chat_created else {}
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers=headers
    )

@router.post("/{chat_id}/stream")
async def stream_message(
    chat_id: str,
    request: MessageStreamRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Stream un message dans un chat existant avec Server-Sent Events (SSE).

    Args:
        chat_id: ID du chat
        request: Requête contenant le message et les paramètres
        current_user: Utilisateur authentifié
        session: Session de streaming (auto-créée et auto-nettoyée)

    Returns:
        StreamingResponse avec media_type="text/event-stream"

    Events SSE émis:
        - event: chunk / data: {"content": "..."}
        - event: sources / data: {"sources": [...]}
        - event: validation_required / data: {"validation_id": "..."}
        - event: stopped / data: {"reason": "user_requested"}
        - event: error / data: {"message": "..."}
        - event: done / data: {}

    Notes:
        - Le stream peut être arrêté via POST /chats/{chat_id}/stop
        - Les validations sont gérées via /validations/{id}/approve|reject|feedback
        - La session est automatiquement nettoyée à la fin du stream
    """
    from app.core.utils.sse import sse_event

    # Vérifier que le chat existe et appartient à l'utilisateur
    chat = await crud.get_chat(chat_id)
    if not chat:
        raise NotFoundError("Chat not found")

    chat = Chat.from_row(chat)
    if chat.user_id != current_user.id:
        raise PermissionError("Not authorized")

    # Vérifier si une génération est déjà en cours
    is_generating = await crud_chats.is_chat_generating(chat_id)
    if is_generating:
        raise ConflictError(
            "Chat is currently generating a response. Please wait before sending a new message."
        )

    # Marquer le chat comme en génération
    await crud_chats.update_chat_generating_status(chat_id, is_generating=True)

    # Check if chat is empty (not initialized)
    if chat.is_empty():
        # Validate agent_id and model are provided
        if not request.agent_id or not request.model:
            raise ValidationError("agent_id and model are required for first message in empty chat")

        # Validate agent exists and belongs to user
        agent = await crud.get_agent(request.agent_id)
        if not agent:
            raise NotFoundError("Agent not found")

        agent = Agent.from_row(agent)
        if agent.user_id != current_user.id and not agent.is_system:
            raise PermissionError("Not authorized to use this agent")

        # Initialize the chat
        success = await crud.initialize_chat(chat_id, request.agent_id, request.model)
        if not success:
            raise AppException("Failed to initialize chat")

        # Reload initialized chat
        chat = await crud.get_chat(chat_id)
        chat = Chat.from_row(chat)

        logger.info(f"✅ Chat {chat_id} initialized with agent={request.agent_id}, model={request.model}")
    else:
        # Check agent hasn't changed (model can change freely)
        if request.agent_id and request.agent_id != chat.agent_id:
            raise ValidationError(f"Cannot change agent in initialized conversation")

    # Sauvegarder message user et récupérer son ID
    user_message_id = await crud.create_message(chat_id, "user", request.message)

    # Mettre à jour le titre si c'est le premier message (titre par défaut)
    if chat.title == "Nouvelle conversation":
        # Utiliser les 50 premiers caractères du message comme titre
        new_title = request.message[:50].strip()
        if len(request.message) > 50:
            new_title += "..."
        await crud_chats.update_chat_title(chat_id, new_title)
        logger.info(f"Chat {chat_id} title updated to: {new_title}")

    # Récupérer l'agent pour le system_prompt
    system_prompt = "Tu es un assistant utile et bienveillant."
    # Utiliser le modèle de la requête si fourni, sinon celui du chat
    model = request.model if request.model else chat.model

    logger.info(f"🔍 DEBUG - Chat {chat_id}: agent_id={chat.agent_id}, team_id={chat.team_id}")

    if chat.agent_id:
        agent = await crud.get_agent(chat.agent_id)
        if agent:
            agent = Agent.from_row(agent)
            system_prompt = agent.system_prompt
            logger.info(f"✅ Agent {chat.agent_id} found: {agent.name}")
            logger.info(f"📝 System prompt (first 100 chars): {system_prompt[:100]}")
        else:
            logger.warning(f"⚠️ Agent {chat.agent_id} not found in database!")
    elif chat.team_id:
        team = await crud.get_team(chat.team_id)
        if team:
            team = Team.from_row(team)
            system_prompt = team.system_prompt
            logger.info(f"✅ Team {chat.team_id} found: {team.name}")
            logger.info(f"📝 System prompt (first 100 chars): {system_prompt[:100]}")
        else:
            logger.warning(f"⚠️ Team {chat.team_id} not found in database!")
    else:
        logger.warning(f"⚠️ Chat {chat_id} has no agent_id or team_id - using default system prompt")

    # === PHASE DE CONSTRUCTION DE CONTEXTE ===
    from app.core.services.contextualizer import contextualizer
    context_data = await contextualizer.build_context(
        chat_id=chat.id,
        agent_id=chat.agent_id,
        team_id=chat.team_id
    )

    # Récupérer les tools depuis le contexte
    tools_for_llm = contextualizer.get_tools_for_llm(context_data)

    # Formater le contexte pour le LLM (ressources uniquement)
    formatted_context = contextualizer.format_context_for_llm(context_data)

    # Stream response
    async def generate():
        # Créer la session de streaming ICI (pas en dependency)
        from app.core.services.llm.manager import stream_manager
        import uuid
        session = stream_manager.start_session(chat_id, current_user.id)

        # Reset sources pour ce nouveau message
        session.reset_sources()

        # Générer un turn_id unique pour ce tour de conversation
        turn_id = str(uuid.uuid4())

        # Initialiser sequence_index dans la session pour partage avec gateway.py
        session.sequence_index = 0

        # Buffer pour le segment de texte en cours
        current_text_buffer = ""
        sources_for_segment = []

        try:

            # Load full message history before streaming
            history = await crud.get_messages_by_chat(chat_id, limit=100)
            # Filtrer les messages tool_call qui ne sont pas supportés par l'API LLM
            # Ces messages sont pour l'UI frontend uniquement
            messages = [
                {"role": msg['role'], "content": msg['content']}
                for msg in history
                if msg['role'] in ('user', 'assistant')
            ]

            # Utiliser stream_chat_with_tools si des tools sont disponibles
            if tools_for_llm:
                from app.core.services.llm.gateway import llm_gateway

                logger.info(f"🚀 Calling LLM with tools - Model: {model}, System prompt: {system_prompt[:50]}...")
                stream_method = llm_gateway.stream_with_tools(
                    messages=messages,
                    model=model,
                    tools=tools_for_llm,
                    system_prompt=system_prompt,
                    api_key_id=request.api_key_id,
                    chat_id=chat.id,
                    user=current_user,
                    agent_id=chat.agent_id,
                    session=session,
                    context_data=context_data,
                    turn_id=turn_id
                )
            else:
                from app.core.services.llm.chat import chat_service
                logger.info(f"🚀 Calling LLM without tools - Model: {model}, System prompt: {system_prompt[:50]}...")
                stream_method = chat_service.stream_chat(
                    messages=messages,
                    system_prompt=system_prompt,
                    model=model,
                    api_key_id=request.api_key_id,
                    context=formatted_context if formatted_context else None
                )

            async for chunk in stream_method:
                # Check stop à chaque chunk
                if session.stop_event.is_set():
                    # Toujours sauvegarder un message stopped, même si buffer vide
                    await crud.create_message(
                        chat_id=chat_id,
                        role="assistant",
                        content=current_text_buffer,  # Peut être vide ""
                        metadata={"stopped": True},
                        turn_id=turn_id,
                        sequence_index=session.sequence_index
                    )

                    yield sse_event("stopped", {"reason": "user_requested"})
                    logger.info(f"Stream stopped by user, buffer saved: {len(current_text_buffer)} chars")
                    break

                # Nouveau: Gérer le signal STREAM_STOPPED venant de gateway.py
                if chunk == "[STREAM_STOPPED]":
                    # Le stop a été détecté dans gateway.py pendant l'attente de validation
                    # Sauvegarder le buffer et envoyer l'event stopped
                    await crud.create_message(
                        chat_id=chat_id,
                        role="assistant",
                        content=current_text_buffer,
                        metadata={"stopped": True},
                        turn_id=turn_id,
                        sequence_index=session.sequence_index
                    )
                    yield sse_event("stopped", {"reason": "user_requested"})
                    logger.info(f"Stream stopped during validation wait")
                    break

                # Parser les events spéciaux et les convertir en SSE
                if chunk.startswith("[VALIDATION_REQUIRED:"):
                    # Format: [VALIDATION_REQUIRED:validation_id:tool_call_message_id]
                    parts = chunk[21:-1].split(":")
                    validation_id = parts[0]
                    tool_call_message_id = parts[1] if len(parts) > 1 else None

                    # TOUJOURS créer le message assistant avant le tool_call (même si vide)
                    logger.info(f"🔵 VALIDATION_REQUIRED | Creating assistant message BEFORE tool_call | turn_id={turn_id} | seq={session.sequence_index}")
                    await crud.create_message(
                        chat_id=chat_id,
                        role="assistant",
                        content=current_text_buffer,  # Peut être vide ""
                        metadata={
                            "sources": sources_for_segment if sources_for_segment else None,
                            "pre_tool_call": True  # Flag pour indiquer que c'est avant un tool
                        },
                        turn_id=turn_id,
                        sequence_index=session.sequence_index
                    )
                    # Reset buffer uniquement (garder les sources pour le message final)
                    current_text_buffer = ""
                    # NE PAS reset sources_for_segment ici - elles seront sauvegardées dans le message final
                    session.sequence_index += 1

                    # Mettre à jour le message tool_call avec turn_id et sequence_index
                    if tool_call_message_id:
                        logger.info(f"🔵 VALIDATION_REQUIRED | Updating tool_call with turn_info | tool_call_id={tool_call_message_id} | turn_id={turn_id} | seq={session.sequence_index}")
                        await crud.update_message_turn_info(
                            message_id=tool_call_message_id,
                            turn_id=turn_id,
                            sequence_index=session.sequence_index
                        )
                        session.sequence_index += 1

                    yield sse_event("validation_required", {"validation_id": validation_id})

                elif chunk.startswith("[STOPPED_BY_USER]"):
                    yield sse_event("stopped", {"reason": "user_requested"})
                    break

                elif chunk.startswith("[TOOL_CALL_CREATED:"):
                    # Format: [TOOL_CALL_CREATED:tool_call_message_id]
                    tool_call_message_id = chunk[19:-1]

                    # EXACTEMENT comme pour VALIDATION_REQUIRED :
                    # 1. Créer message assistant AVANT le tool_call
                    logger.info(f"🟢 TOOL_CALL_CREATED | Creating assistant message BEFORE tool_call | turn_id={turn_id} | seq={session.sequence_index}")
                    await crud.create_message(
                        chat_id=chat_id,
                        role="assistant",
                        content=current_text_buffer,  # Peut être vide ""
                        metadata={
                            "sources": sources_for_segment if sources_for_segment else None,
                            "pre_tool_call": True  # Flag pour indiquer que c'est avant un tool
                        },
                        turn_id=turn_id,
                        sequence_index=session.sequence_index
                    )
                    # Reset buffer uniquement (garder les sources pour le message final)
                    current_text_buffer = ""
                    session.sequence_index += 1

                    # 2. Mettre à jour le message tool_call avec turn_id et sequence_index
                    logger.info(f"🟢 TOOL_CALL_CREATED | Updating tool_call with turn_info | tool_call_id={tool_call_message_id} | turn_id={turn_id} | seq={session.sequence_index}")
                    await crud.update_message_turn_info(
                        message_id=tool_call_message_id,
                        turn_id=turn_id,
                        sequence_index=session.sequence_index
                    )
                    session.sequence_index += 1

                    # 3. Notifier le frontend
                    yield sse_event("tool_call_created", {})
                    logger.debug("Tool call message created and ordered correctly")

                elif chunk == "[TOOL_CALL_UPDATED]":
                    # Un message tool_call vient d'être mis à jour, notifier le frontend pour refetch
                    yield sse_event("tool_call_updated", {})
                    logger.debug("Tool call message updated, frontend notified")

                elif chunk.startswith("[SOURCES:"):
                    sources_json = chunk[9:-1]
                    if sources_json.strip():
                        sources_for_segment = json.loads(sources_json)
                        yield sse_event("sources", {"sources": sources_for_segment})
                        logger.debug(f"Received sources: {len(sources_for_segment)} resource(s)")
                    else:
                        logger.debug("Empty sources event, skipping")

                else:
                    # Texte normal → accumuler dans le buffer
                    current_text_buffer += chunk
                    yield sse_event("chunk", {"content": chunk})

            # Finaliser le stream si terminé normalement (sans stop)
            if not session.stop_event.is_set():
                # Sauvegarder le dernier buffer s'il contient du texte
                if current_text_buffer.strip():
                    await crud.create_message(
                        chat_id=chat_id,
                        role="assistant",
                        content=current_text_buffer,
                        metadata={"sources": sources_for_segment} if sources_for_segment else None,
                        turn_id=turn_id,
                        sequence_index=session.sequence_index
                    )

                # Mettre à jour le modèle du chat si changé (cache du dernier modèle utilisé)
                if request.model and request.model != chat.model:
                    await crud_chats.update_chat_model(chat.id, request.model)

            # Event final "done"
            yield sse_event("done", {})

        except Exception as e:
            logger.exception("Stream error")
            yield sse_event("error", {"message": str(e)})

        finally:
            # Nettoyer la session et le statut de génération
            session = stream_manager.get_session(chat_id)

            if session and session.pending_validation_id:
                # Validation en attente : garder session mais marquer comme déconnectée
                session.is_active = False
                session.disconnected_at = datetime.now()
                logger.info(
                    f"Stream disconnected but validation {session.pending_validation_id} pending, "
                    f"keeping session for chat {chat_id}"
                )
                # Ne pas marquer is_generating=False car génération peut reprendre après validation
            else:
                # Pas de validation : supprimer normalement
                stream_manager.end_session(chat_id)
                logger.info(f"Stream session properly ended for chat {chat_id}")
                # Marquer génération terminée
                await crud_chats.update_chat_generating_status(chat_id, is_generating=False)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.post("/{chat_id}/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Arrête un stream en cours pour ce chat et force is_generating = false.

    Fonctionne même sans session active (génération background, validation, etc.).

    Args:
        chat_id: ID du chat
        current_user: Utilisateur authentifié

    Returns:
        204 No Content (toujours succès)

    Raises:
        404: Chat not found
        403: Not authorized

    Side effects:
        - Set le stop_event de la session (si existe)
        - Force is_generating = false en DB (toujours)
        - Le stream s'arrêtera et yieldera [STOPPED_BY_USER] (si session active)
        - Log type='stream_stop' créé (avec flag 'forced' si pas de session)
    """
    # Vérifier que le chat existe et appartient à l'utilisateur
    chat = await crud.get_chat(chat_id)
    if not chat:
        raise NotFoundError("Chat not found")

    chat = Chat.from_row(chat)
    if chat.user_id != current_user.id:
        raise PermissionError("Not authorized")

    # Arrêter le stream via le manager (si session active)
    from app.core.services.llm.manager import stream_manager

    stopped = stream_manager.stop_stream(chat_id)

    # Auto-refuser toutes les validations en attente pour ce chat
    from app.database.crud import validations as crud_validations
    from app.database.crud import chats as crud_chats
    cancelled_validations = await crud_validations.get_pending_validations_for_chat(chat_id)

    if cancelled_validations:
        # Annuler les validations en DB
        await crud_validations.cancel_all_pending_validations(
            chat_id,
            reason="user_stopped_stream"
        )

        # Mettre à jour les messages tool_call correspondants
        from datetime import datetime
        for validation in cancelled_validations:
            tool_call_message = await crud_chats.get_message_by_validation_id(validation['id'])
            if tool_call_message:
                history = tool_call_message.metadata.get("history", [])
                history.append({
                    "step": "cancelled",
                    "timestamp": datetime.utcnow().isoformat(),
                    "reason": "user_stopped_stream"
                })

                await crud_chats.update_message_metadata(
                    message_id=tool_call_message.id,
                    metadata_updates={
                        "step": "cancelled",
                        "status": "cancelled",
                        "history": history
                    }
                )

        logger.info(f"Auto-cancelled {len(cancelled_validations)} pending validation(s) and updated messages for chat {chat_id}")

    # TOUJOURS remettre is_generating à false, même si pas de session active
    # (cas: génération background, validation en cours, stream crashé, etc.)
    await crud_chats.update_chat_generating_status(chat_id, is_generating=False)

    # Logger l'arrêt avec info si c'était un force stop
    await crud.create_log(
        user_id=current_user.id,
        log_type="stream_stop",
        data={
            "reason": "user_requested",
            "had_active_session": stopped,
            "forced": not stopped
        },
        agent_id=chat.agent_id,
        chat_id=chat_id
    )

    if not stopped:
        logger.warning(f"Force stopped chat {chat_id} without active session (background generation or stale state)")

    return None


@router.get("/{chat_id}", response_model=ChatResponse)
async def get(chat_id: str, current_user: User = Depends(get_current_user)):
    """Récupère une conversation par ID."""
    chat = await crud.get_chat(chat_id)
    if not chat:
        raise NotFoundError("Chat not found")

    chat = Chat.from_row(chat)

    # Vérifier que le chat appartient à l'utilisateur
    if chat.user_id != current_user.id:
        raise PermissionError("Not authorized to access this chat")

    return ChatResponse(**chat.to_dict())

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(chat_id: str, current_user: User = Depends(get_current_user)):
    """Supprime une conversation."""
    chat = await crud.get_chat(chat_id)
    if not chat:
        raise NotFoundError("Chat not found")

    chat = Chat.from_row(chat)

    # Vérifier que le chat appartient à l'utilisateur
    if chat.user_id != current_user.id:
        raise PermissionError("Not authorized to delete this chat")

    success = await crud.delete_chat(chat_id)
    if not success:
        raise AppException("Failed to delete chat")

    return None

@router.post("/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: str,
    request: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    """Envoie un message dans une conversation."""
    # Vérifier que le chat existe et appartient à l'utilisateur
    chat = await crud.get_chat(chat_id)
    if not chat:
        raise NotFoundError("Chat not found")

    chat = Chat.from_row(chat)
    if chat.user_id != current_user.id:
        raise PermissionError("Not authorized")

    # Créer le message
    message_id = await crud.create_message(
        chat_id=chat_id,
        role=request.role,
        content=request.content,
        metadata=request.metadata
    )

    message = await crud.get_messages_by_chat(chat_id, limit=1)
    if not message:
        raise AppException("Failed to create message")

    # Récupérer le dernier message créé
    messages = await crud.get_messages_by_chat(chat_id, limit=100)
    message = Message.from_row([m for m in messages if m['id'] == message_id][0])

    return MessageResponse(**message.to_dict())

@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def messages(
    chat_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Récupère les messages d'une conversation."""
    # Vérifier que le chat existe et appartient à l'utilisateur
    chat = await crud.get_chat(chat_id)
    if not chat:
        raise NotFoundError("Chat not found")

    chat = Chat.from_row(chat)
    if chat.user_id != current_user.id:
        raise PermissionError("Not authorized")

    messages = await crud.get_messages_by_chat(chat_id, limit=limit)
    response = [MessageResponse(**Message.from_row(m).to_dict()) for m in messages]

    # LOG: Vérifier l'ordre avant envoi au frontend
    logger.info(f"📤 SENDING TO FRONTEND | chat_id={chat_id} | count={len(response)}")
    for i, msg in enumerate(response):
        logger.info(f"   [{i}] role={msg.role} | turn_id={msg.turn_id} | seq={msg.sequence_index}")

    return response
