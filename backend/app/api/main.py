#!/usr/bin/env python3
# app/api/main.py

import uvicorn
import asyncpg
from pathlib import Path
from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from config.config import settings
from config.logger import logger
from app.api.v1.routes import auth, users, health, agents, teams, chats, uploads, resources, validations, servers, models, api_keys, services, user_providers, oauth, automations
from app.api.v1.routes.internal.mcp import rag_router, automation_router
from app.database.db import init_db
from app.database.migrations import run_pending_migrations
from app.core.utils.scheduler import app_scheduler
from app.core.services.llm.sync import daily_model_sync_job
from app.core.services.chats.cleanup import daily_empty_chats_cleanup_job
from app.core.init import initialize_system_resources
from app.core.system import sync_internal_infrastructure
from app.core.services.automation.scheduler import load_cron_triggers
from app.core.jobs.cleanup import expire_validations
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import AppException
from app.api.v1.exception_handlers import app_exception_handler, validation_exception_handler
from app.core.utils.http_client import init_http_client, close_http_client

async def lifespan(app: FastAPI):
   logger.info("🚀 Démarrage de l'application")
   await init_db()

   # Create database connection pool
   logger.info("🔗 Creating database connection pool...")
   app.state.db_pool = await asyncpg.create_pool(
       host=settings.db_host,
       port=settings.db_port,
       database=settings.db_name,
       user=settings.db_user,
       password=settings.db_password,
       min_size=10,
       max_size=50,
       timeout=60,
       command_timeout=30,
       server_settings={
           'search_path': 'core, agents, chat, mcp, resources, audit, public'
       }
   )
   logger.info(f"✅ Database pool created: min=10, max=50")

   # Initialize HTTP client pool
   await init_http_client()

   # Re-initialize LLM adapters with pooled HTTP client
   from app.core.services.llm.gateway import llm_gateway
   await llm_gateway.reinit_with_pooled_client()

   # Exécuter les migrations en attente
   logger.info("🔄 Vérification des migrations...")
   await run_pending_migrations()

   # Synchroniser TOUTE l'infrastructure système (source unique)
   await sync_internal_infrastructure()

   # Démarrer le scheduler
   logger.info("📅 Configuration du scheduler...")
   app_scheduler.add_job(
       daily_model_sync_job,
       'cron',
       hour=0,
       minute=0,
       id='daily_model_sync'
   )
   app_scheduler.add_job(
       daily_empty_chats_cleanup_job,
       'cron',
       hour=1,
       minute=0,
       id='daily_empty_chats_cleanup',
       kwargs={'days': 30}
   )
   app_scheduler.add_job(
       expire_validations,
       'interval',
       minutes=15,
       id='cleanup_expired_validations'
   )
   app_scheduler.start()

   # Charger les triggers CRON des automations
   logger.info("🔧 Chargement des triggers CRON...")
   await load_cron_triggers()

   # Vérifier les outils CLI pour MCP
   from app.core.services.mcp.manager import ServerManager
   logger.info("🔧 Checking MCP runtime tools...")

   tools = await ServerManager.check_prerequisites()

   logger.info("📦 MCP Runtime Tools:")
   logger.info(f"  {'✅' if tools.get('npx') else '❌'} npx (Node.js packages from npm)")
   logger.info(f"  {'✅' if tools.get('uvx') else '❌'} uvx (Python packages from PyPI)")
   logger.info(f"  {'✅' if tools.get('docker') else '❌'} docker (Container runtime)")

   if not tools.get('npx'):
       logger.warning("   ⚠️  npx not found. Install: https://nodejs.org/")

   if not tools.get('uvx'):
       logger.warning("   ⚠️  uvx not found. Install: pip install uv")

   if not tools.get('docker'):
       logger.warning("   ⚠️  docker not found. Install: https://docker.com/get-started")

   logger.info("✅ Startup complete")

   yield

   # Close HTTP client pool
   await close_http_client()

   # Close database connection pool
   logger.info("🔗 Closing database connection pool...")
   await app.state.db_pool.close()
   logger.info("✅ Database pool closed")

   # Arrêter le scheduler proprement
   logger.info("🛑 Arrêt du scheduler...")
   app_scheduler.shutdown()
   logger.info("🛑 Arrêt de l'application")

# --- Création de l'app ---
app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

# --- Handler d'exceptions globales ---
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# --- Configuration CORS ---
# Liste des origines autorisées
allowed_origins = [
    "http://localhost:3000",  # Frontend dev
    "http://127.0.0.1:3000",  # Frontend dev alternative
]

# Ajouter l'URL du frontend en production si définie
if settings.frontend_url:
    allowed_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Confirm-Deletion"],
    expose_headers=["Content-Type"],
    max_age=3600,  # Cache preflight 1h
)

# --- Middleware de logging des requêtes (DEBUG uniquement) ---
if settings.debug:
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.debug(f"{request.method} {request.url.path}")
        response = await call_next(request)
        return response

# --- Création du router principal v1 ---
api_v1_router = APIRouter(prefix="/api/v1")

# --- Création du router internal ---
internal_router = APIRouter(prefix="/api/internal")

# --- Inclusion des routes dans v1 ---
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(agents.router)
api_v1_router.include_router(teams.router)
api_v1_router.include_router(chats.router)
api_v1_router.include_router(uploads.router)
api_v1_router.include_router(resources.router)
api_v1_router.include_router(validations.router)
api_v1_router.include_router(servers.router)
api_v1_router.include_router(oauth.router)
api_v1_router.include_router(models.router)
api_v1_router.include_router(api_keys.router)
api_v1_router.include_router(services.router)
api_v1_router.include_router(user_providers.router)
api_v1_router.include_router(automations.router)

# --- Uploads directory creation (files served via authenticated API endpoint) ---
upload_path = Path(settings.upload_dir).resolve()
upload_path.mkdir(parents=True, exist_ok=True)
# StaticFiles mount removed - uploads served via /api/v1/uploads/{file_id} with JWT authentication

# --- Montage des routers MCP internes ---
internal_router.include_router(rag_router)
internal_router.include_router(automation_router)

# --- Montage du router v1, internal et health (hors versioning) ---
app.include_router(api_v1_router)
app.include_router(internal_router)
app.include_router(health.router)  # Health check reste hors versioning

# --- Lancement en mode script ---
if __name__ == "__main__":
    uvicorn.run("app.api.main:app", host=settings.host, port=settings.port, reload=settings.debug, factory=False)