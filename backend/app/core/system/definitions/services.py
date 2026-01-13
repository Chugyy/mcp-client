#!/usr/bin/env python3
"""
Définitions des services système (LLM providers).
Source unique de vérité.
"""

SYSTEM_SERVICES = [
    {
        "id": "svc_openai",
        "name": "OpenAI",
        "provider": "openai",
        "description": "OpenAI API - GPT-4o, GPT-4, GPT-3.5 Turbo",
        "status": "active"
    },
    {
        "id": "svc_anthropic",
        "name": "Anthropic",
        "provider": "anthropic",
        "description": "Anthropic API - Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku",
        "status": "active"
    }
]
