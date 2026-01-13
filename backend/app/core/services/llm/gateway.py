# app/core/llm/gateway.py
"""Gateway LLM principal - Point d'entrée unifié pour tous les providers."""

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, List, Dict, Any, Optional
from config.config import settings
from config.logger import logger


class ValidationPendingException(Exception):
    """
    Exception levée quand une validation est requise dans une automation.
    Permet de sortir proprement du stream pour mettre l'execution en pause.
    """
    def __init__(self, validation_id: str, execution_id: str):
        self.validation_id = validation_id
        self.execution_id = execution_id
        super().__init__(f"Validation {validation_id} required for execution {execution_id}")
from .registry import get_provider_from_model, get_provider_config
from .adapters.openai import OpenAIAdapter
from .adapters.anthropic import AnthropicAdapter
from .utils.params import transform_params, extract_model_params
from .utils.router import Router
from .types import ToolDefinition, ToolCall, ToolResult
from .utils.messages import (
    append_tool_call_for_anthropic,
    append_tool_results_for_anthropic,
    append_tool_call_for_openai,
    append_tool_results_for_openai
)
from app.core.utils.circuit_breaker import CircuitBreaker, CircuitState


class LLMGateway:
    """
    Gateway unifié pour accéder à tous les providers LLM.
    Gère le routing, fallback, retry et transformation des paramètres.
    """

    # Instructions universelles pour la gestion des outils et erreurs
    TOOL_ERROR_HANDLING_INSTRUCTIONS = """

# TOOL ERROR HANDLING INSTRUCTIONS

When you receive an error after calling a tool, follow these guidelines:

## 1. Missing Parameter Errors
Example: "Missing required parameter: X"
- Extract the missing parameter from the conversation history
- If you have the information: Retry immediately with the correct parameter
- If you don't have it: Ask the user explicitly for the missing information

## 2. Invalid Parameter Errors
Example: "Invalid value for X"
- Review the tool's input schema carefully
- Check parameter type, format, and constraints
- Retry with a valid parameter value
- If unsure: Explain the constraint to the user and ask for clarification

## 3. Technical/Connection Errors
Example: "Connection failed", "Timeout", "Internal error"
- Inform the user about the temporary issue
- Suggest alternative approaches if available
- DO NOT retry immediately (avoid infinite loops)
- Wait for user guidance

## 4. User Feedback
When you receive user feedback about a tool call:
- Read the feedback carefully
- Adjust your parameters according to their input
- Retry with the corrected approach
- Acknowledge the feedback in your response

## Important Notes
- You have multiple attempts to succeed - use them intelligently
- Always explain to the user what went wrong and what you're doing to fix it
- If you exhaust all attempts, provide a clear summary of what failed and why
"""

    def __init__(self):
        """Initialise le gateway avec les adapters admin depuis settings."""
        self.adapters = {}
        self.router = Router(max_retries=3)

        # Initialize circuit breakers per provider
        self.circuit_breakers = {
            "anthropic": CircuitBreaker(
                name="anthropic",
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=1
            ),
            "openai": CircuitBreaker(
                name="openai",
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=1
            )
        }

        # Initialiser les adapters admin depuis settings (.env)
        self._init_admin_adapters()

    def _enrich_system_prompt(self, base_prompt: Optional[str], has_tools: bool) -> str:
        """
        Enrichit le prompt système avec des instructions universelles.

        Args:
            base_prompt: Prompt système de l'agent (optionnel)
            has_tools: Si True, ajoute les instructions de gestion d'erreurs

        Returns:
            Prompt enrichi
        """
        if not base_prompt:
            base_prompt = "You are a helpful AI assistant."

        if has_tools:
            return f"{base_prompt}\n{self.TOOL_ERROR_HANDLING_INSTRUCTIONS}"

        return base_prompt

    def _init_admin_adapters(self):
        """Initialise les adapters depuis settings (.env)."""
        if settings.openai_api_key:
            self.adapters["openai"] = OpenAIAdapter(settings.openai_api_key)
            logger.info("✅ OpenAI adapter initialized (admin)")

        if settings.anthropic_api_key:
            self.adapters["anthropic"] = AnthropicAdapter(settings.anthropic_api_key)
            logger.info("✅ Anthropic adapter initialized (admin)")

        if not self.adapters:
            logger.warning("⚠️ No LLM adapters initialized. Check your API keys.")

    async def reinit_with_pooled_client(self):
        """Re-initialize admin adapters with pooled HTTP client after pool is created."""
        from app.core.utils.http_client import get_http_client

        try:
            http_client = await get_http_client()

            if settings.openai_api_key:
                self.adapters["openai"] = OpenAIAdapter(settings.openai_api_key, http_client=http_client)
                logger.info("✅ OpenAI adapter re-initialized with pooled HTTP client")

            if settings.anthropic_api_key:
                self.adapters["anthropic"] = AnthropicAdapter(settings.anthropic_api_key, http_client=http_client)
                logger.info("✅ Anthropic adapter re-initialized with pooled HTTP client")

        except RuntimeError as e:
            logger.warning(f"Could not re-initialize adapters with pooled client: {e}")

    async def _get_adapter_for_provider(self, provider: str, api_key_id: Optional[str] = None):
        """
        Récupère ou crée un adapter pour un provider.

        Args:
            provider: Le provider (openai, anthropic)
            api_key_id: ID de la clé API en DB, ou None/"admin" pour settings

        Returns:
            Adapter configuré
        """
        # Si admin ou None: utiliser les adapters préinitialisés depuis settings
        if api_key_id is None or api_key_id == "admin":
            if provider not in self.adapters:
                raise ValueError(f"Provider '{provider}' not configured in settings. Check API keys.")
            return self.adapters[provider]

        # Sinon: récupérer la clé depuis DB et créer adapter dynamique avec pooled client
        from app.database import crud
        from app.core.utils.http_client import get_http_client

        api_key = await crud.get_api_key_decrypted(api_key_id)
        if not api_key:
            raise ValueError(f"API key '{api_key_id}' not found in database")

        # Get pooled HTTP client
        try:
            http_client = await get_http_client()
        except RuntimeError:
            # Pool not initialized yet, create adapter without it
            http_client = None
            logger.warning(f"HTTP client pool not available, creating {provider} adapter without pooling")

        # Créer adapter avec la clé DB et pooled client
        if provider == "openai":
            return OpenAIAdapter(api_key, http_client=http_client)
        elif provider == "anthropic":
            return AnthropicAdapter(api_key, http_client=http_client)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _call_with_circuit_breaker(self, provider: str, func, *args, **kwargs):
        """
        Wrap async function call with circuit breaker protection.

        Args:
            provider: Provider name (e.g., "anthropic", "openai")
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func execution

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        circuit = self.circuit_breakers.get(provider)
        if not circuit:
            # No circuit breaker for this provider, execute directly
            return await func(*args, **kwargs)

        return await circuit.call(func, *args, **kwargs)

    async def _check_circuit_state(self, provider: str):
        """
        Check circuit breaker state before streaming.

        If circuit is OPEN and recovery timeout has passed, transition to HALF_OPEN.
        Otherwise, raise CircuitBreakerOpenError.

        Args:
            provider: Provider name (e.g., "anthropic", "openai")

        Raises:
            CircuitBreakerOpenError: If circuit is OPEN and recovery timeout not reached
        """
        circuit = self.circuit_breakers.get(provider)
        if not circuit:
            return

        async with circuit._lock:
            if circuit.state == CircuitState.OPEN:
                if circuit._should_attempt_reset():
                    circuit.state = CircuitState.HALF_OPEN
                    circuit.success_count = 0
                    logger.info(f"Circuit breaker {provider}: OPEN → HALF_OPEN")
                else:
                    seconds_until_retry = circuit._seconds_until_retry()
                    from app.core.exceptions import CircuitBreakerOpenError
                    raise CircuitBreakerOpenError(
                        f"Provider {provider} is temporarily unavailable. Retry in {seconds_until_retry}s."
                    )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        system_prompt: Optional[str] = None,
        api_key_id: Optional[str] = "admin",
        **params
    ) -> AsyncGenerator[str, None]:
        """
        Stream une réponse LLM avec retry automatique.

        Args:
            messages: Liste des messages [{"role": "user", "content": "..."}]
            model: Nom du modèle à utiliser
            system_prompt: Prompt système optionnel
            api_key_id: ID de la clé API (None/"admin" = settings, sinon = DB)
            **params: Paramètres unifiés (temperature, max_tokens, top_p, etc.)

        Yields:
            str: Chunks de texte au fur et à mesure

        Example:
            ```python
            async for chunk in gateway.stream(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-4o-mini",
                api_key_id="admin",
                temperature=0.7,
                max_tokens=2000
            ):
                print(chunk, end="")
            ```
        """
        # Déterminer le provider du modèle
        provider = get_provider_from_model(model)

        # Récupérer l'adapter
        adapter = await self._get_adapter_for_provider(provider, api_key_id)

        # Ajouter le modèle aux paramètres
        params["model"] = model

        # Transformer les paramètres pour le provider
        adapted_params = transform_params(provider, params)

        # Transformer les messages selon le provider
        if provider == "anthropic":
            messages_to_send, extra_params = adapter.transform_messages(messages, system_prompt)
            adapted_params.update(extra_params)
        else:
            messages_to_send = adapter.transform_messages(messages, system_prompt)

        # Check circuit breaker before streaming
        await self._check_circuit_state(provider)
        circuit = self.circuit_breakers.get(provider)

        # Stream with retry
        stream_success = False
        try:
            async for chunk in self.router.stream_with_retry(
                adapter,
                messages_to_send,
                adapted_params
            ):
                yield chunk
            stream_success = True
        except Exception as e:
            if circuit:
                await circuit.record_failure()
            logger.error(f"Stream failed for {provider}: {e}")
            raise
        finally:
            if circuit and stream_success:
                await circuit.record_success()

    async def list_models(self, provider: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Liste tous les modèles disponibles par provider.

        Args:
            provider: Provider spécifique ou None pour tous

        Returns:
            Dict: {"openai": [...], "anthropic": [...]}
        """
        results = {}

        providers_to_query = [provider] if provider else self.adapters.keys()

        for prov in providers_to_query:
            if prov not in self.adapters:
                logger.warning(f"Provider '{prov}' not configured, skipping")
                continue

            try:
                models = await self.adapters[prov].list_models()
                results[prov] = models
                logger.info(f"✅ Listed {len(models)} models from {prov}")
            except Exception as e:
                logger.error(f"Failed to list models from {prov}: {e}")
                results[prov] = []

        return results

    async def stream_with_tools(
        self,
        messages: List[Dict[str, str]],
        model: str,
        tools: List[ToolDefinition],
        system_prompt: Optional[str] = None,
        api_key_id: Optional[str] = "admin",
        max_iterations: int = 25,
        max_consecutive_errors: int = 5,
        chat_id: Optional[str] = None,
        user: Optional[Any] = None,
        agent_id: Optional[str] = None,
        session: Optional[Any] = None,
        context_data: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        **params
    ) -> AsyncGenerator[str, None]:
        """
        Stream une réponse LLM avec support des tool calls et validation humaine.

        Gère automatiquement :
        - Détection des tool calls dans le stream
        - Vérification des permissions (permission_level + cache)
        - Demande de validation si nécessaire (avec attente asynchrone)
        - Exécution via MCP après validation
        - Continuation du stream avec les résultats
        - Arrêt sur demande utilisateur (stop_event)

        Args:
            messages: Liste des messages
            model: Nom du modèle
            tools: Liste des tools disponibles
            system_prompt: Prompt système optionnel
            api_key_id: ID de la clé API
            max_iterations: Limite absolue d'itérations pour éviter les boucles infinies (défaut: 50)
            max_consecutive_errors: Nombre max d'erreurs consécutives avant arrêt (défaut: 5)
            chat_id: ID du chat (requis pour validation)
            user: Objet User (requis pour validation)
            agent_id: ID de l'agent (optionnel)
            session: StreamSession pour gestion stop/validation (optionnel)
            **params: Paramètres supplémentaires

        Yields:
            str: Chunks de texte OU events JSON pour validation

        Events spéciaux yielded:
            - [VALIDATION_REQUIRED:{validation_id}] : Validation en attente
            - [STOPPED_BY_USER] : Arrêt demandé par utilisateur
            - [VALIDATION_EXPIRED] : Timeout de validation (15 jours)
        """
        # Déterminer le provider
        provider = get_provider_from_model(model)

        # Récupérer l'adapter
        adapter = await self._get_adapter_for_provider(provider, api_key_id)

        # Log des tools reçus
        logger.info(f"stream_with_tools called with {len(tools)} tools: {[t.name for t in tools]}")

        # Créer un registre pour retrouver les server_id des tools
        tool_registry = {tool.name: tool.server_id for tool in tools if tool.server_id}

        # Préparer les paramètres
        params["model"] = model
        adapted_params = transform_params(provider, params)

        # Enrichir le system prompt avec instructions de gestion d'erreurs
        enriched_prompt = self._enrich_system_prompt(system_prompt, has_tools=len(tools) > 0)

        # Transformer les messages avec le prompt enrichi
        if provider == "anthropic":
            messages_to_send, extra_params = adapter.transform_messages(messages, enriched_prompt)
            adapted_params.update(extra_params)
        else:
            messages_to_send = adapter.transform_messages(messages, enriched_prompt)

        # Check circuit breaker before starting tool calling loop
        await self._check_circuit_state(provider)
        circuit = self.circuit_breakers.get(provider)

        # Import du ValidationService
        from app.core.utils.validation import validation_service

        # Boucle d'itération
        iteration = 0
        consecutive_errors = 0

        while iteration < max_iterations and consecutive_errors < max_consecutive_errors:
            iteration += 1
            logger.debug(f"Tool calling iteration {iteration}/{max_iterations} (consecutive errors: {consecutive_errors}/{max_consecutive_errors})")

            # Check stop event
            if session and session.stop_event.is_set():
                logger.info("Stream stopped by user")
                yield "[STOPPED_BY_USER]"
                break

            tool_calls_detected = []

            # Stream avec détection de tool calls
            async for chunk in adapter.stream_with_tools(
                messages_to_send,
                tools,
                **adapted_params
            ):
                # Check stop à chaque chunk
                if session and session.stop_event.is_set():
                    logger.info("Stream stopped by user during LLM generation")
                    yield "[STOPPED_BY_USER]"
                    break

                if isinstance(chunk, str):
                    # Texte normal → yield au client
                    yield chunk

                elif isinstance(chunk, ToolCall):
                    # Tool call détecté → accumuler
                    tool_calls_detected.append(chunk)
                    logger.info(f"Tool call detected: {chunk.name}")

            # Si stop demandé, sortir
            if session and session.stop_event.is_set():
                break

            # Si aucun tool call, on arrête
            if not tool_calls_detected:
                logger.debug("No more tool calls, streaming complete")
                break

            # Exécuter les tools avec gestion de validation
            logger.info(f"Processing {len(tool_calls_detected)} tool call(s)")
            tool_results = []

            for tool_call in tool_calls_detected:
                try:
                    # Trouver le server_id
                    server_id = tool_registry.get(tool_call.name)
                    if not server_id:
                        logger.error(f"Tool {tool_call.name} not found in registry")
                        tool_results.append(ToolResult(
                            tool_call_id=tool_call.id,
                            content=f"Error: Tool {tool_call.name} not found",
                            is_error=True
                        ))
                        continue

                    # ===== SYSTÈME DE VALIDATION =====

                    # 1. Vérifier si validation nécessaire
                    should_execute = True
                    validation_id = None

                    if user and chat_id:
                        should_execute, reason = await validation_service.should_execute_tool(
                            user=user,
                            agent_id=agent_id,
                            tool_name=tool_call.name,
                            server_id=server_id
                        )

                        if not should_execute:
                            if reason == "permission_denied":
                                # User a no_tools, bloquer complètement
                                tool_results.append(ToolResult(
                                    tool_call_id=tool_call.id,
                                    content="Tool execution denied: user permission level is 'no_tools'",
                                    is_error=True
                                ))
                                logger.warning(f"Tool {tool_call.name} denied: no_tools permission")
                                continue

                            elif reason == "validation_required":
                                # Créer une validation et attendre
                                # Pour les internal tools, server_id doit être None (pas "__internal__")
                                db_server_id = None if server_id == "__internal__" else server_id
                                validation_id, tool_call_message_id = await validation_service.create_validation_request(
                                    user_id=user.id,
                                    chat_id=chat_id,
                                    agent_id=agent_id,
                                    tool_name=tool_call.name,
                                    server_id=db_server_id,
                                    tool_call_id=tool_call.id,
                                    arguments=tool_call.arguments,
                                    execution_id=execution_id
                                )

                                # Marquer la validation en attente dans la session
                                if session:
                                    session.pending_validation_id = validation_id
                                    logger.info(f"Session {chat_id} now waiting for validation {validation_id}")

                                # Yield event de validation avec message_id pour mise à jour turn_info
                                logger.info(f"🟡 YIELDING [VALIDATION_REQUIRED] | validation_id={validation_id} | tool_call_message_id={tool_call_message_id}")
                                yield f"[VALIDATION_REQUIRED:{validation_id}:{tool_call_message_id}]"

                                # Si automation (execution_id présent), lever exception au lieu d'attendre
                                if execution_id:
                                    logger.info(f"⏸️ Validation required in automation {execution_id}, pausing execution")
                                    raise ValidationPendingException(validation_id, execution_id)

                                # Attendre la validation avec timeout de 48h (chat seulement)
                                if session:
                                    # Attendre soit validation_event, soit stop_event
                                    done, pending = await asyncio.wait(
                                        [
                                            asyncio.create_task(session.validation_event.wait()),
                                            asyncio.create_task(session.stop_event.wait())
                                        ],
                                        timeout=48 * 3600,  # 48h
                                        return_when=asyncio.FIRST_COMPLETED
                                    )

                                    # Annuler les tasks en attente
                                    for task in pending:
                                        task.cancel()

                                    # Vérifier quel événement a été déclenché
                                    if session.stop_event.is_set():
                                        # Stream arrêté par l'utilisateur
                                        logger.info(f"Stream stopped during validation wait for validation {validation_id}")

                                        # Marquer le message tool_call comme 'cancelled'
                                        from app.database.crud import chats as crud_chats
                                        tool_call_message = await crud_chats.get_message_by_validation_id(validation_id)

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

                                        # Retourner un signal spécial au stream
                                        yield "[STREAM_STOPPED]"
                                        return

                                    elif session.validation_event.is_set():
                                        # Validation reçue, continuer normalement
                                        pass
                                    else:
                                        # Timeout (48h) - rejeter automatiquement
                                        logger.warning(f"Validation timeout after 48h for {validation_id}")

                                    # Récupérer le résultat de validation
                                    validation_result = session.validation_result

                                    if not validation_result:
                                        logger.error("Validation event set but no result found")
                                        tool_results.append(ToolResult(
                                            tool_call_id=tool_call.id,
                                            content="Validation error: no result",
                                            is_error=True
                                        ))
                                        continue

                                    action = validation_result.get("action")

                                    if action == "approved":
                                        # Validation approuvée, récupérer le résultat d'exécution
                                        exec_result = validation_result.get("data")

                                        if exec_result and exec_result.get("success"):
                                            # Parser le format MCP pour les tools internes
                                            result_content = exec_result.get("result")

                                            if server_id == "__internal__":
                                                # Format MCP: {"content": [{"type": "text", "text": "...JSON..."}]}
                                                if isinstance(result_content, dict) and "content" in result_content:
                                                    try:
                                                        content_text = result_content["content"][0]["text"]
                                                        parsed_content = content_text
                                                        logger.info(f"Parsed MCP format for validated tool {tool_call.name}")
                                                    except (KeyError, IndexError, TypeError) as e:
                                                        logger.error(f"Failed to parse MCP format: {e}")
                                                        parsed_content = json.dumps(result_content)
                                                else:
                                                    parsed_content = json.dumps(result_content)
                                            else:
                                                parsed_content = json.dumps(result_content)

                                            tool_results.append(ToolResult(
                                                tool_call_id=tool_call.id,
                                                content=parsed_content,
                                                is_error=False
                                            ))
                                            logger.info(f"Tool {tool_call.name} executed after validation")
                                        else:
                                            tool_results.append(ToolResult(
                                                tool_call_id=tool_call.id,
                                                content=f"Error: {exec_result.get('error', 'Unknown error')}",
                                                is_error=True
                                            ))

                                        # Reset validation event pour prochaine validation
                                        session.validation_event.clear()
                                        session.validation_result = None
                                        session.pending_validation_id = None
                                        logger.debug(f"Validation resolved for session {chat_id}")

                                    elif action == "rejected":
                                        # Validation rejetée → ARRÊTER COMPLÈTEMENT le stream
                                        logger.info(f"Tool {tool_call.name} rejected by user - STOPPING stream")

                                        # Reset validation event
                                        session.validation_event.clear()
                                        session.validation_result = None
                                        session.pending_validation_id = None

                                        # Annuler toutes les autres validations pending de ce chat
                                        if chat_id:
                                            from app.database import crud
                                            cancelled_count = await crud.cancel_all_pending_validations(
                                                chat_id=chat_id,
                                                reason="user_rejected_tool"
                                            )
                                            if cancelled_count > 0:
                                                logger.info(f"Cancelled {cancelled_count} other pending validations after rejection")

                                        # Yield un message explicatif
                                        yield "\n\n[Action refusée par l'utilisateur. Génération arrêtée.]"

                                        # STOP : sortir complètement de la boucle de tool calling
                                        return

                                    elif action == "feedback":
                                        # Feedback reçu, créer un ToolResult avec le feedback
                                        # Le LLM recevra le feedback comme résultat et pourra décider
                                        feedback_text = validation_result.get("data", {}).get("feedback", "User provided feedback")

                                        tool_results.append(ToolResult(
                                            tool_call_id=tool_call.id,
                                            content=f"""TOOL EXECUTION BLOCKED BY USER

The user has provided feedback instead of approving the tool execution:
"{feedback_text}"

IMPORTANT: The tool '{tool_call.name}' was NOT executed.
You must:
1. Acknowledge the user's feedback
2. Adjust your approach based on their input
3. Either propose a modified tool call or take a different action

Do not proceed as if the tool was executed.""",
                                            is_error=False
                                        ))
                                        logger.info(f"Feedback received for tool {tool_call.name}: {feedback_text}")

                                        # Reset validation event
                                        session.validation_event.clear()
                                        session.validation_result = None
                                        session.pending_validation_id = None
                                        logger.debug(f"Validation resolved for session {chat_id}")
                                else:
                                    # Pas de session, on ne peut pas attendre
                                    logger.error("Validation required but no session provided")
                                    tool_results.append(ToolResult(
                                        tool_call_id=tool_call.id,
                                        content="Validation required but session not available",
                                        is_error=True
                                    ))
                                    continue

                    # 2. Exécution directe (si permission full_auto ou cache hit)
                    if should_execute:
                        from app.core.services.mcp.clients import execute_tool

                        # ===== CRÉER MESSAGE TOOL_CALL POUR FULL_AUTO =====
                        # Créer un message tool_call visible même pour les exécutions directes
                        # SANS turn_id/sequence_index (seront ajoutés par chats.py)
                        tool_call_message_id = None
                        if chat_id:
                            from app.database import crud
                            content = f"Utilisation de l'outil : {tool_call.name}"

                            metadata = {
                                "step": "executing",
                                "tool_call_id": tool_call.id,
                                "tool_name": tool_call.name,
                                "server_id": server_id if server_id != "__internal__" else None,
                                "arguments": tool_call.arguments,
                                "status": "executing",
                                "auto_approved": True,  # Flag pour indiquer exécution automatique
                                "history": [
                                    {
                                        "step": "executing",
                                        "timestamp": datetime.utcnow().isoformat(),
                                        "status": "auto_approved"
                                    }
                                ]
                            }

                            logger.info(f"🟢 CREATING TOOL_CALL MESSAGE (full_auto) | tool_name={tool_call.name} | WITHOUT turn_info yet")
                            tool_call_message_id = await crud.create_message(
                                chat_id=chat_id,
                                role="tool_call",
                                content=content,
                                metadata=metadata
                                # turn_id et sequence_index seront ajoutés par chats.py
                            )

                            # Notifier le frontend avec l'ID du message
                            yield f"[TOOL_CALL_CREATED:{tool_call_message_id}]"

                        # Ajouter resource_ids pour internal tools
                        tool_arguments = tool_call.arguments.copy()
                        if server_id == "__internal__" and context_data:
                            all_resources = context_data.get("resources", [])
                            resource_ids = [r['id'] for r in all_resources if r.get('status') == 'ready']
                            tool_arguments["_resource_ids"] = resource_ids
                            logger.info(f"🔍 [Resource IDs] Total resources in context: {len(all_resources)}, ready: {len(resource_ids)}, ids: {resource_ids}")

                        # Log pour debug user_id
                        user_id_to_pass = user.id if user else None
                        logger.info(f"🔍 [LLM Gateway] User object: {user}, User ID: {user_id_to_pass}")
                        if user:
                            logger.info(f"🔍 [LLM Gateway] User attributes: {dir(user)}")

                        result = await execute_tool(
                            server_id=server_id,
                            tool_name=tool_call.name,
                            arguments=tool_arguments,
                            user_id=user_id_to_pass
                        )

                        # Log du résultat pour debug
                        logger.info(f"🔍 [Tool Result] server_id={server_id}, tool={tool_call.name}, success={result.get('success')}")
                        logger.debug(f"🔍 [Tool Result] Full result: {result}")

                        # ===== EXTRACTION DES SOURCES (RAG) =====
                        if server_id == "__internal__" and tool_call.name == "search_resources" and result.get("success"):
                            rag_result = result.get("result", {})

                            # Parser le format MCP : {"content": [{"type": "text", "text": "...JSON..."}]}
                            detailed_sources = []
                            if "content" in rag_result and len(rag_result["content"]) > 0:
                                try:
                                    content_text = rag_result["content"][0].get("text", "{}")
                                    parsed_data = json.loads(content_text)
                                    detailed_sources = parsed_data.get("detailed_sources", [])
                                    logger.info(f"Parsed {len(detailed_sources)} detailed source(s) from MCP response")
                                except (json.JSONDecodeError, KeyError, IndexError) as e:
                                    logger.error(f"Failed to parse MCP response for sources: {e}")
                                    detailed_sources = []

                            # Accumuler les sources détaillées dans la session
                            if session and detailed_sources:
                                # Stocker les sources détaillées (format frontend)
                                if not hasattr(session, 'detailed_sources'):
                                    session.detailed_sources = []

                                session.detailed_sources.extend(detailed_sources)
                                logger.info(f"Accumulated {len(detailed_sources)} detailed source(s), total: {len(session.detailed_sources)}")

                        # Log l'exécution directe
                        if user and chat_id:
                            from app.database import crud
                            await crud.create_log(
                                user_id=user.id,
                                log_type="tool_call",
                                data={
                                    "tool_name": tool_call.name,
                                    "server_id": server_id,
                                    "args": tool_call.arguments,
                                    "result": result,
                                    "status": "executed" if result["success"] else "error",
                                    "always_allow": False  # Exécution directe ne cache pas
                                },
                                agent_id=agent_id,
                                chat_id=chat_id
                            )

                        # ===== METTRE À JOUR LE MESSAGE TOOL_CALL =====
                        if tool_call_message_id and chat_id:
                            from app.database.crud import chats as crud_chats
                            tool_call_message = await crud_chats.get_message(tool_call_message_id)

                            if tool_call_message:
                                final_step = "completed" if result["success"] else "failed"
                                # tool_call_message est un objet Message
                                metadata = tool_call_message.metadata or {}
                                history = metadata.get("history", [])
                                history.append({
                                    "step": final_step,
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "result": result
                                })

                                await crud_chats.update_message_metadata(
                                    message_id=tool_call_message_id,
                                    metadata_updates={
                                        "step": final_step,
                                        "status": final_step,
                                        "result": result,
                                        "history": history
                                    }
                                )
                                logger.info(f"🟢 UPDATED TOOL_CALL MESSAGE (full_auto) | step={final_step}")

                                # Notifier le frontend de la mise à jour
                                yield "[TOOL_CALL_UPDATED]"

                        if result["success"]:
                            # Parser le format MCP pour les tools internes
                            result_content = result["result"]

                            if server_id == "__internal__":
                                # Format MCP: {"content": [{"type": "text", "text": "...JSON..."}]}
                                if isinstance(result_content, dict) and "content" in result_content:
                                    try:
                                        content_text = result_content["content"][0]["text"]
                                        # Le contenu est déjà un JSON string, on le passe tel quel au LLM
                                        parsed_content = content_text
                                        logger.info(f"Parsed MCP format for internal tool {tool_call.name}")
                                    except (KeyError, IndexError, TypeError) as e:
                                        logger.error(f"Failed to parse MCP format: {e}")
                                        parsed_content = json.dumps(result_content)
                                else:
                                    # Fallback si pas au format MCP
                                    parsed_content = json.dumps(result_content)
                            else:
                                # Tools externes: sérialiser normalement
                                parsed_content = json.dumps(result_content)

                            tool_results.append(ToolResult(
                                tool_call_id=tool_call.id,
                                content=parsed_content,
                                is_error=False
                            ))
                            logger.info(f"Tool {tool_call.name} executed directly")
                        else:
                            error_msg = result['error']
                            remaining = max_consecutive_errors - consecutive_errors - 1  # -1 car cette erreur va incrémenter

                            # Format enrichi pour aider le LLM à comprendre et corriger
                            enriched_error = f"""TOOL EXECUTION ERROR

Tool: {tool_call.name}
Error: {error_msg}

ANALYSIS:
- If this is a "Missing required parameter" error: Check the conversation history and retry with the correct parameter
- If this is an "Invalid parameter" error: Review the tool's schema and retry with valid values
- If this is a technical error (connection, timeout, etc.): Inform the user and suggest alternatives

You have {remaining} consecutive error(s) remaining before stopping. Use them wisely."""

                            tool_results.append(ToolResult(
                                tool_call_id=tool_call.id,
                                content=enriched_error,
                                is_error=True
                            ))
                            logger.error(f"Tool {tool_call.name} failed: {result['error']}")

                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    remaining = max_consecutive_errors - consecutive_errors - 1  # -1 car cette erreur va incrémenter

                    enriched_error = f"""TOOL EXECUTION EXCEPTION

Tool: {tool_call.name}
Exception: {str(e)}

DIAGNOSTIC: An unexpected error occurred while executing this tool.
- This might be a temporary issue with the tool's backend
- Review your parameters and ensure they are valid
- If the error persists, inform the user

You have {remaining} consecutive error(s) remaining before stopping."""

                    tool_results.append(ToolResult(
                        tool_call_id=tool_call.id,
                        content=enriched_error,
                        is_error=True
                    ))

            # Vérifier s'il y a eu des erreurs dans cette itération
            has_errors = any(tr.is_error for tr in tool_results)

            if has_errors:
                consecutive_errors += 1
                logger.warning(f"Iteration {iteration} had errors. Consecutive errors: {consecutive_errors}/{max_consecutive_errors}")
            else:
                # Succès : réinitialiser le compteur d'erreurs consécutives
                if consecutive_errors > 0:
                    logger.info(f"Iteration {iteration} succeeded. Resetting consecutive errors counter (was {consecutive_errors})")
                consecutive_errors = 0

            # Construire les messages de continuation
            if provider == "anthropic":
                messages_to_send = append_tool_call_for_anthropic(
                    messages_to_send, tool_calls_detected
                )
                messages_to_send = append_tool_results_for_anthropic(
                    messages_to_send, tool_results
                )
            else:  # OpenAI
                messages_to_send = append_tool_call_for_openai(
                    messages_to_send, tool_calls_detected
                )
                messages_to_send = append_tool_results_for_openai(
                    messages_to_send, tool_results
                )

            # Continuer le stream avec les résultats
            logger.debug("Continuing stream with tool results")

        # Messages de fin de boucle
        if consecutive_errors >= max_consecutive_errors:
            logger.warning(f"Max consecutive errors ({max_consecutive_errors}) reached, stopping tool calling loop")
        elif iteration >= max_iterations:
            logger.warning(f"Max iterations ({max_iterations}) reached, stopping tool calling loop")

        # ===== ÉMETTRE LES SOURCES À LA FIN DU STREAM =====
        if session and hasattr(session, 'detailed_sources') and session.detailed_sources:
            sources_json = json.dumps(session.detailed_sources)
            yield f"[SOURCES:{sources_json}]"
            logger.info(f"Emitted {len(session.detailed_sources)} detailed source(s)")

        # Record successful completion for circuit breaker
        if circuit:
            await circuit.record_success()


# Instance globale réutilisable
llm_gateway = LLMGateway()
