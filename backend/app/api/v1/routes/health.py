#!/usr/bin/env python3
# app/api/routes/health.py

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from config.config import settings
from app.core.services.llm.gateway import llm_gateway

router = APIRouter(prefix="", tags=["health"])

@router.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name, "version": "1.0.0"}

@router.get("/health/circuit-breakers")
async def get_circuit_breaker_status():
    """
    Return circuit breaker status for all LLM providers.

    Returns HTTP 200 if all circuits are CLOSED (healthy).
    Returns HTTP 503 if any circuit is OPEN (degraded).
    """
    statuses = {}
    all_closed = True

    for name, circuit in llm_gateway.circuit_breakers.items():
        state = circuit.get_state()
        statuses[name] = state
        if state["state"] != "closed":
            all_closed = False

    status_code = 200 if all_closed else 503
    return JSONResponse(
        content={
            "status": "healthy" if all_closed else "degraded",
            "circuit_breakers": statuses
        },
        status_code=status_code
    )