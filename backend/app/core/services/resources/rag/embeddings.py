"""Génération d'embeddings avec AsyncOpenAI."""

import asyncio
from typing import List
from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.config import settings
from config.logger import logger

# Initialize AsyncOpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
    reraise=True
)
async def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for a single text using async OpenAI client.

    Args:
        text: Input text to embed

    Returns:
        List of floats representing the embedding vector (3072 dimensions)

    Raises:
        RateLimitError: When API rate limit is exceeded
        APITimeoutError: When request times out
        APIConnectionError: When connection to API fails
        Exception: For other API errors
    """
    try:
        logger.debug(f"Generating embedding for text (length: {len(text)} chars)")
        start_time = asyncio.get_event_loop().time()

        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=text,
            timeout=30.0
        )

        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time

        embedding = response.data[0].embedding

        # Log success with timing and token usage
        logger.info(
            f"Embedding generated successfully",
            extra={
                "elapsed_seconds": round(elapsed, 2),
                "model": settings.embedding_model,
                "dimensions": len(embedding),
                "prompt_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') else None
            }
        )

        # Padding if dimension < 3072 (for pgvector compatibility)
        target_dim = settings.embedding_dim
        if len(embedding) < target_dim:
            embedding = embedding + [0.0] * (target_dim - len(embedding))
            logger.debug(f"Padded embedding from {len(response.data[0].embedding)} to {target_dim} dimensions")

        return embedding

    except (RateLimitError, APITimeoutError, APIConnectionError) as e:
        logger.warning(
            f"Retriable error during embedding generation: {type(e).__name__}",
            extra={"error": str(e), "text_length": len(text)}
        )
        raise
    except Exception as e:
        logger.error(
            f"Embedding generation failed: {type(e).__name__}",
            extra={"error": str(e), "text_length": len(text)},
            exc_info=True
        )
        raise


async def embed_texts(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """
    Génère embeddings via AsyncOpenAI pour une liste de textes.

    Args:
        texts: List of texts to embed
        batch_size: Maximum number of concurrent embedding requests (default: 100)

    Returns:
        List of embedding vectors, one per input text

    Note:
        Processes texts in batches to avoid overwhelming the API with concurrent requests.
        Empty input returns empty list.
    """
    if not texts:
        logger.debug("Empty texts list provided, returning empty embeddings")
        return []

    logger.info(f"Starting batch embedding generation for {len(texts)} texts")
    start_time = asyncio.get_event_loop().time()

    embeddings = []

    # Process in batches to control concurrency
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(texts) + batch_size - 1) // batch_size

        logger.debug(f"Processing batch {batch_num}/{total_batches} ({len(batch)} texts)")

        # Generate embeddings concurrently within batch
        batch_embeddings = await asyncio.gather(*[
            generate_embedding(text) for text in batch
        ])

        embeddings.extend(batch_embeddings)

    end_time = asyncio.get_event_loop().time()
    elapsed = end_time - start_time

    logger.info(
        f"Batch embedding generation complete",
        extra={
            "total_texts": len(texts),
            "total_embeddings": len(embeddings),
            "elapsed_seconds": round(elapsed, 2),
            "avg_time_per_text": round(elapsed / len(texts), 3)
        }
    )

    return embeddings
