# app/core/llm/registry.py
"""Registry des capacités et limites de chaque provider LLM."""

from typing import Dict, List, Any

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "temperature": {"min": 0.0, "max": 2.0, "default": 1.0},
        "max_tokens": {"max": 16000, "default": 4000},
        "top_p": {"min": 0.0, "max": 1.0, "default": 1.0},
        "supports": ["temperature", "top_p", "max_tokens", "stop", "frequency_penalty", "presence_penalty"],
        "pricing": {
            "gpt-4o": {"input": 5.0, "output": 20.0},
            "gpt-4o-mini": {"input": 0.60, "output": 2.40},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        },
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
    },
    "anthropic": {
        "name": "Anthropic",
        "temperature": {"min": 0.0, "max": 1.0, "default": 1.0},
        "max_tokens": {"max": 4096, "default": 2048},
        "top_p": {"min": 0.0, "max": 1.0, "default": 1.0},
        "top_k": {"min": 0, "max": 500, "default": 40},
        "supports": ["temperature", "top_p", "top_k", "max_tokens", "stop_sequences"],
        "pricing": {
            "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
            "claude-opus-4-5": {"input": 15.0, "output": 75.0},
            "claude-haiku-3-5": {"input": 0.80, "output": 4.0},
        },
        "models": [
            "claude-sonnet-4-5-20250929",
            "claude-opus-4-5",
            "claude-haiku-3-5",
        ],
    },
}


def get_provider_from_model(model: str) -> str:
    """Détecte le provider à partir du nom du modèle."""
    if model.startswith("gpt-"):
        return "openai"
    elif model.startswith("claude-"):
        return "anthropic"
    else:
        raise ValueError(f"Unknown model: {model}. Cannot determine provider.")


def get_provider_config(provider: str) -> Dict[str, Any]:
    """Récupère la configuration d'un provider."""
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    return PROVIDERS[provider]


def get_supported_params(provider: str) -> List[str]:
    """Récupère la liste des paramètres supportés par un provider."""
    config = get_provider_config(provider)
    return config["supports"]


def validate_param(provider: str, param_name: str, value: Any) -> Any:
    """Valide et ajuste un paramètre selon les limites du provider."""
    config = get_provider_config(provider)

    # Vérifier que le paramètre est supporté
    if param_name not in config.get("supports", []):
        return None  # Paramètre non supporté, on l'ignore

    # Valider et ajuster selon les limites
    if param_name == "temperature":
        limits = config["temperature"]
        return max(limits["min"], min(limits["max"], value))

    elif param_name == "max_tokens":
        limits = config["max_tokens"]
        return min(limits["max"], value)

    elif param_name == "top_p":
        limits = config["top_p"]
        return max(limits["min"], min(limits["max"], value))

    elif param_name == "top_k":
        if "top_k" in config:
            limits = config["top_k"]
            return max(limits["min"], min(limits["max"], value))
        return None

    return value
