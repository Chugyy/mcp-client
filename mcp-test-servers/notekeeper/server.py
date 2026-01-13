#!/usr/bin/env python3
"""
Notekeeper MCP Server - Streamable HTTP avec OAuth 2.1
Converti de ProMCP Backup 2 pour Docker MCP Toolkit
"""
import os
import sys
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.exceptions import ResourceError
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse, FileResponse
from jose import jwt
import os.path

from database import init_db, NoteRepository

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("notekeeper-mcp")

init_db()

# Configuration de l'authentification Stytch avec JWTVerifier
auth = JWTVerifier(
    jwks_uri=f"{os.getenv('STYTCH_DOMAIN', 'https://api.stytch.com')}/.well-known/jwks.json",
    issuer=os.getenv("STYTCH_DOMAIN", "https://api.stytch.com"),
    algorithm="RS256",
    audience=os.getenv("STYTCH_PROJECT_ID", "project-test-default")
)

# Configuration MCP avec authentification OAuth
mcp = FastMCP("notekeeper", auth=auth)

def get_current_user_id() -> str:
    access_token: AccessToken = get_access_token()
    return jwt.get_unverified_claims(access_token.token)["sub"]

@mcp.tool()
def create_note(title: str, content: str, category: str = "general") -> str:
    try:
        user_id = get_current_user_id()
        note = NoteRepository.create_note(user_id, title, content, category)
        logger.info(f"Created note {note.id} for user {user_id}")
        return f"✅ Note created successfully (ID: {note.id})"
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        return f"❌ Error creating note: {str(e)}"

@mcp.tool()
def get_notes(category: str = "", search: str = "", limit: str = "10") -> str:
    try:
        user_id = get_current_user_id()
        limit_int = min(int(limit) if limit.isdigit() else 10, 50)
        notes = NoteRepository.get_notes_by_user(user_id, category, search, limit_int)
        
        if not notes:
            return "📝 No notes found matching your criteria"
        
        result = f"📝 Found {len(notes)} note(s):\n\n"
        for note in notes:
            result += f"[{note.id}] {note.title}\n"
            result += f"   Category: {note.category}\n"
            result += f"   Updated: {note.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
            result += f"   Content: {note.content[:100]}{'...' if len(note.content) > 100 else ''}\n\n"
        
        return result
    except Exception as e:
        logger.error(f"Error getting notes: {e}")
        return f"❌ Error retrieving notes: {str(e)}"

@mcp.tool()
def update_note(id: str, title: str = "", content: str = "", category: str = "") -> str:
    try:
        user_id = get_current_user_id()
        note = NoteRepository.update_note(user_id, int(id), title, content, category)
        
        if not note:
            return f"❌ Note {id} not found"
        
        logger.info(f"Updated note {id} for user {user_id}")
        return f"✅ Note {id} updated successfully"
    except Exception as e:
        logger.error(f"Error updating note: {e}")
        return f"❌ Error updating note: {str(e)}"

@mcp.tool()
def delete_note(id: str) -> str:
    try:
        user_id = get_current_user_id()
        success = NoteRepository.delete_note(user_id, int(id))
        
        if not success:
            return f"❌ Note {id} not found"
        
        logger.info(f"Archived note {id} for user {user_id}")
        return f"✅ Note {id} archived successfully"
    except Exception as e:
        logger.error(f"Error deleting note: {e}")
        return f"❌ Error deleting note: {str(e)}"

@mcp.tool()
def search_notes(query: str, category: str = "") -> str:
    try:
        user_id = get_current_user_id()
        notes = NoteRepository.get_notes_by_user(user_id, category, query, 20)
        
        if not notes:
            return f"🔍 No notes found for query: '{query}'"
        
        result = f"🔍 Search results for '{query}' ({len(notes)} found):\n\n"
        for note in notes:
            title_highlight = note.title.replace(query, f"**{query}**") if query.lower() in note.title.lower() else note.title
            result += f"[{note.id}] {title_highlight}\n"
            result += f"   Category: {note.category} | {note.updated_at.strftime('%Y-%m-%d')}\n"
            result += f"   Preview: {note.content[:150]}{'...' if len(note.content) > 150 else ''}\n\n"
        
        return result
    except Exception as e:
        logger.error(f"Error searching notes: {e}")
        return f"❌ Error searching notes: {str(e)}"

@mcp.tool()
def get_categories() -> str:
    try:
        user_id = get_current_user_id()
        categories = NoteRepository.get_categories(user_id)
        
        if not categories:
            return "📋 No categories found"
        
        result = "📋 Your note categories:\n\n"
        for category, count in categories:
            result += f"   {category}: {count} note(s)\n"
        
        return result
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return f"❌ Error getting categories: {str(e)}"

@mcp.resource(uri="file:///notes/export.json", name="notes_export", description="JSON export of all user notes")
async def export_notes_json() -> str:
    try:
        user_id = get_current_user_id()
        notes = NoteRepository.get_notes_by_user(user_id, limit=1000)
        
        export_data = {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "total_notes": len(notes),
            "notes": [
                {
                    "id": note.id,
                    "title": note.title,
                    "content": note.content,
                    "category": note.category,
                    "created_at": note.created_at.isoformat(),
                    "updated_at": note.updated_at.isoformat()
                }
                for note in notes
            ]
        }
        
        return json.dumps(export_data, indent=2)
    except Exception as e:
        raise ResourceError(f"Error exporting notes: {str(e)}")

@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET", "OPTIONS"])
def oauth_metadata(request: StarletteRequest) -> JSONResponse:
    # Construire l'URL complète avec HTTPS et le path /mcp
    base_url = str(request.base_url).rstrip("/")
    # Forcer HTTPS si on est derrière ngrok
    if "ngrok" in base_url and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://")
    
    resource_url = f"{base_url}/mcp"
    
    return JSONResponse(
        {
            "resource": resource_url,
            "authorization_servers": [os.getenv("STYTCH_DOMAIN", "https://api.stytch.com")],
            "scopes_supported": ["read", "write"],
            "bearer_methods_supported": ["header"]
        }
    )

@mcp.custom_route("/health", methods=["GET"])
def health_check(request: StarletteRequest) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "notekeeper"})

# Servir le frontend statique (ne pas intercepter /mcp/)
@mcp.custom_route("/", methods=["GET"])
def serve_index(request: StarletteRequest):
    """Servir la page d'accueil"""
    static_path = os.path.join(os.path.dirname(__file__), "frontend/dist/index.html")
    if os.path.exists(static_path):
        return FileResponse(static_path)
    return JSONResponse({"error": "Frontend not built. Run: cd frontend && npm install && npm run build"}, status_code=404)

@mcp.custom_route("/assets/{path:path}", methods=["GET"])
def serve_assets(request: StarletteRequest):
    """Servir les assets statiques"""
    path = request.path_params.get("path", "")
    static_dir = os.path.join(os.path.dirname(__file__), "frontend/dist/assets")
    file_path = os.path.join(static_dir, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return JSONResponse({"error": "Asset not found"}, status_code=404)

# Configuration des middlewares pour fastmcp v2.x
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"], 
        allow_headers=["*"],
    )
]

# Note: fastmcp v2.x utilise mcp.run() directement, pas d'objet app nécessaire

if __name__ == "__main__":
    logger.info("Starting NoteKeeper MCP server with Stytch authentication...")

    port = int(os.environ.get('PORT', 8081))
    
    try:
        # Pattern fastmcp v2.x direct
        mcp.run(transport="http", host="0.0.0.0", port=port, middleware=middleware)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)