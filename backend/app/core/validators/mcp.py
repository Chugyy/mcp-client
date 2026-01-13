#!/usr/bin/env python3
# app/core/validators/mcp.py
"""
Alias pour ServerValidator (réexporte depuis services/mcp/validator).

Ce module permet d'importer ServerValidator depuis app.core.validators.mcp
tout en gardant l'implémentation dans app.core.services.mcp.validator.
"""

from app.core.services.mcp.validator import ServerValidator, ALLOWED_SERVER_TYPES

__all__ = ['ServerValidator', 'ALLOWED_SERVER_TYPES']
