# app/core/llm/utils/params.py
"""Transformation et validation des paramètres LLM."""

from typing import Dict, Any
from ..registry import get_provider_config, get_supported_params, validate_param


def transform_params(provider: str, unified_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforme les paramètres unifiés vers le format spécifique du provider.

    Args:
        provider: Nom du provider (openai, anthropic)
        unified_params: Paramètres au format unifié

    Returns:
        Dict: Paramètres adaptés au provider
    """
    config = get_provider_config(provider)
    supported = get_supported_params(provider)
    adapted_params = {}

    # Paramètres requis qui doivent toujours être préservés
    required_params = ["model"]

    # Mapping des noms de paramètres si nécessaire
    param_mapping = {
        "openai": {
            "stop": "stop",
            "max_tokens": "max_tokens",
            "temperature": "temperature",
            "top_p": "top_p",
        },
        "anthropic": {
            "stop": "stop_sequences",
            "max_tokens": "max_tokens",
            "temperature": "temperature",
            "top_p": "top_p",
            "top_k": "top_k",
        },
    }

    mapping = param_mapping.get(provider, {})

    for unified_key, value in unified_params.items():
        # Mapper le nom du paramètre
        provider_key = mapping.get(unified_key, unified_key)

        # Toujours inclure les paramètres requis
        if provider_key in required_params:
            adapted_params[provider_key] = value
            continue

        # Vérifier si supporté
        if provider_key not in supported:
            continue

        # Valider et ajuster la valeur
        validated_value = validate_param(provider, provider_key, value)

        if validated_value is not None:
            adapted_params[provider_key] = validated_value

    # Injecter les defaults pour les paramètres requis par le provider
    if provider == "anthropic" and "max_tokens" not in adapted_params:
        adapted_params["max_tokens"] = config["max_tokens"]["default"]
    elif provider == "openai" and "max_tokens" not in adapted_params:
        adapted_params["max_tokens"] = config["max_tokens"]["default"]

    return adapted_params


def extract_model_params(all_params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    Extrait le modèle et les autres paramètres.

    Args:
        all_params: Tous les paramètres fournis

    Returns:
        tuple: (model, other_params)
    """
    params = all_params.copy()
    model = params.pop("model", None)

    if not model:
        raise ValueError("Parameter 'model' is required")

    return model, params
