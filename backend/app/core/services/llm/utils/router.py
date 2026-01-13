# app/core/llm/utils/router.py
"""Router pour gérer les fallbacks et retry logic."""

import asyncio
from typing import AsyncGenerator, List, Dict, Any
from config.logger import logger
from ..adapters.base import BaseAdapter


class Router:
    """Gère le routing, fallback et retry des requêtes LLM."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    async def stream_with_retry(
        self,
        adapter: BaseAdapter,
        messages: List[Dict[str, str]],
        params: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        Stream avec retry automatique sur erreurs retriables.

        Args:
            adapter: L'adapter à utiliser
            messages: Messages à envoyer
            params: Paramètres de la requête

        Yields:
            str: Chunks de texte
        """
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry {attempt + 1}/{self.max_retries} for {adapter.__class__.__name__}")

                async for chunk in adapter.stream(messages, **params):
                    yield chunk

                # Si on arrive ici, le streaming a réussi
                return

            except Exception as e:
                # Vérifier si l'erreur est retriable
                if adapter.is_retriable_error(e):
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(
                            f"{adapter.__class__.__name__} error (retriable): {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            f"{adapter.__class__.__name__} failed after {self.max_retries} retries"
                        )
                        raise
                else:
                    # Erreur non retriable, on lève immédiatement
                    logger.error(f"{adapter.__class__.__name__} non-retriable error: {e}")
                    raise
