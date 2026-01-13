#!/usr/bin/env python3
# app/core/services/mcp/oauth_manager.py

import httpx
import hashlib
import base64
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any
from urllib.parse import urlencode
from app.database.db import get_connection
from app.core.utils.oauth_cache import get_cached_metadata
from config.logger import logger

TIMEOUT = 30.0


class OAuthManager:
    """Complete OAuth MCP flow management."""

    # ===== OAUTH FLOW =====

    @staticmethod
    def generate_pkce() -> Dict[str, str]:
        """
        Generate PKCE (Proof Key for Code Exchange) parameters.

        Returns:
            {
                "code_verifier": str (128 chars),
                "code_challenge": str (base64url encoded SHA256)
            }
        """
        # Generate code_verifier (43-128 characters)
        code_verifier = ''.join(
            secrets.choice(string.ascii_letters + string.digits + '-._~')
            for _ in range(128)
        )

        # Generate code_challenge (SHA256 hash of verifier, base64url encoded)
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')

        return {
            "code_verifier": code_verifier,
            "code_challenge": code_challenge
        }

    @staticmethod
    def generate_state() -> str:
        """Generate random state to prevent CSRF attacks."""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

    @staticmethod
    async def discover_metadata(url: str) -> Dict[str, Any]:
        """
        Trigger 401 on /mcp/ to retrieve WWW-Authenticate header.

        Args:
            url: MCP server base URL (ex: http://localhost:8081)

        Returns:
            {
                "success": bool,
                "resource_metadata_url": str,  # URL of .well-known/oauth-protected-resource
                "error": Optional[str]
            }
        """
        from app.core.utils.http_client import get_http_client

        mcp_url = f"{url.rstrip('/')}/mcp/"

        try:
            client = await get_http_client()
        except RuntimeError:
            # Fallback if pool not initialized
            logger.warning("HTTP client pool not available, using temporary client")
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
                try:
                    logger.info(f"Triggering 401 on {mcp_url} to discover OAuth metadata")
                    response = await client.post(
                        mcp_url,
                        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
                    )
                    # Continue with same logic...
                    if response.status_code == 401:
                        www_auth = response.headers.get('www-authenticate', '')
                        logger.debug(f"WWW-Authenticate header: {www_auth}")
                        if 'resource_metadata=' in www_auth:
                            start = www_auth.index('resource_metadata="') + len('resource_metadata="')
                            end = www_auth.index('"', start)
                            resource_metadata_url = www_auth[start:end]
                            logger.info(f"Discovered resource metadata URL: {resource_metadata_url}")
                            return {"success": True, "resource_metadata_url": resource_metadata_url, "error": None}
                        else:
                            resource_metadata_url = f"{url.rstrip('/')}/.well-known/oauth-protected-resource"
                            logger.warning(f"No resource_metadata in WWW-Authenticate, using default: {resource_metadata_url}")
                            return {"success": True, "resource_metadata_url": resource_metadata_url, "error": None}
                    else:
                        return {"success": False, "resource_metadata_url": None, "error": f"Expected 401, got {response.status_code}"}
                except Exception as e:
                    logger.error(f"Error discovering OAuth metadata: {e}")
                    return {"success": False, "resource_metadata_url": None, "error": str(e)}

        # Use pooled client
        try:
            logger.info(f"Triggering 401 on {mcp_url} to discover OAuth metadata")

            # Request without token to trigger 401
            response = await client.post(
                mcp_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                follow_redirects=True
            )

            if response.status_code == 401:
                # Retrieve WWW-Authenticate header
                www_auth = response.headers.get('www-authenticate', '')
                logger.debug(f"WWW-Authenticate header: {www_auth}")

                # Parse header to extract resource_metadata
                # Expected format: Bearer resource_metadata="https://..."
                if 'resource_metadata=' in www_auth:
                    # Extract URL from quotes
                    start = www_auth.index('resource_metadata="') + len('resource_metadata="')
                    end = www_auth.index('"', start)
                    resource_metadata_url = www_auth[start:end]

                    logger.info(f"Discovered resource metadata URL: {resource_metadata_url}")
                    return {
                        "success": True,
                        "resource_metadata_url": resource_metadata_url,
                        "error": None
                    }
                else:
                    # No resource_metadata, use default .well-known
                    resource_metadata_url = f"{url.rstrip('/')}/.well-known/oauth-protected-resource"
                    logger.warning(f"No resource_metadata in WWW-Authenticate, using default: {resource_metadata_url}")
                    return {
                        "success": True,
                        "resource_metadata_url": resource_metadata_url,
                        "error": None
                    }

        except Exception as e:
            logger.error(f"Error discovering OAuth metadata: {e}")
            return {
                "success": False,
                "resource_metadata_url": None,
                "error": str(e)
            }

    @staticmethod
    async def fetch_protected_resource(url: str) -> Dict[str, Any]:
        """
        Fetch protected resource metadata (MCP server) with caching.

        Args:
            url: URL of .well-known/oauth-protected-resource

        Returns:
            {
                "success": bool,
                "resource": str,  # MCP resource URL
                "authorization_servers": List[str],  # Authorization server URLs
                "error": Optional[str]
            }
        """
        async def _fetch_metadata(metadata_url: str) -> dict:
            """Internal fetcher for cache layer."""
            from app.core.utils.http_client import get_http_client

            client = await get_http_client()
            logger.info(f"Fetching protected resource metadata: {metadata_url}")
            response = await client.get(metadata_url)

            if response.status_code == 200:
                metadata = response.json()

                # Verify required fields
                if 'resource' in metadata and 'authorization_servers' in metadata:
                    logger.info(f"Protected resource metadata: {metadata}")
                    return {
                        "success": True,
                        "resource": metadata['resource'],
                        "authorization_servers": metadata['authorization_servers'],
                        "scopes_supported": metadata.get('scopes_supported', []),
                        "error": None
                    }
                else:
                    raise ValueError("Missing required fields in protected resource metadata")
            else:
                raise Exception(f"HTTP {response.status_code}")

        try:
            # Use cached metadata with fallback to stale cache on failure
            return await get_cached_metadata(url, _fetch_metadata)

        except Exception as e:
            logger.error(f"Error fetching protected resource metadata: {e}")
            return {
                "success": False,
                "resource": None,
                "authorization_servers": [],
                "error": str(e)
            }

    @staticmethod
    async def fetch_authorization_server(url: str) -> Dict[str, Any]:
        """
        Fetch authorization server metadata with caching.

        Args:
            url: Authorization server URL (ex: https://thread-towel-4950.customers.stytch.dev)

        Returns:
            {
                "success": bool,
                "authorization_endpoint": str,
                "token_endpoint": str,
                "jwks_uri": str,
                "error": Optional[str]
            }
        """
        metadata_url = f"{url.rstrip('/')}/.well-known/oauth-authorization-server"

        async def _fetch_metadata(cache_url: str) -> dict:
            """Internal fetcher for cache layer."""
            from app.core.utils.http_client import get_http_client

            client = await get_http_client()
            logger.info(f"Fetching authorization server metadata: {cache_url}")
            response = await client.get(cache_url)

            if response.status_code == 200:
                metadata = response.json()

                logger.info(f"Authorization server metadata: {metadata}")
                return {
                    "success": True,
                    "authorization_endpoint": metadata.get('authorization_endpoint'),
                    "token_endpoint": metadata.get('token_endpoint'),
                    "jwks_uri": metadata.get('jwks_uri'),
                    "scopes_supported": metadata.get('scopes_supported', []),
                    "error": None
                }
            else:
                raise Exception(f"HTTP {response.status_code}")

        try:
            # Use cached metadata with fallback to stale cache on failure
            return await get_cached_metadata(metadata_url, _fetch_metadata)

        except Exception as e:
            logger.error(f"Error fetching authorization server metadata: {e}")
            return {
                "success": False,
                "authorization_endpoint": None,
                "token_endpoint": None,
                "jwks_uri": None,
                "error": str(e)
            }

    @staticmethod
    def build_auth_url(
        authorization_endpoint: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        state: str,
        scope: str = "read write"
    ) -> str:
        """
        Build OAuth 2.1 authorization URL with PKCE.

        Args:
            authorization_endpoint: OAuth server authorization endpoint
            client_id: Client ID (can be a URL per MCP standard)
            redirect_uri: Callback URI
            code_challenge: PKCE challenge
            state: State to prevent CSRF
            scope: Requested scopes

        Returns:
            Complete authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "scope": scope,
            "state": state
        }

        auth_url = f"{authorization_endpoint}?{urlencode(params)}"
        logger.info(f"Built authorization URL: {auth_url}")

        return auth_url

    @staticmethod
    async def exchange_code(
        token_endpoint: str,
        code: str,
        redirect_uri: str,
        code_verifier: str,
        client_id: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            token_endpoint: OAuth server token endpoint
            code: Authorization code received via callback
            redirect_uri: Callback URI (must match)
            code_verifier: PKCE verifier
            client_id: Client ID

        Returns:
            {
                "success": bool,
                "access_token": str,
                "refresh_token": str,
                "token_type": str,
                "expires_in": int,
                "scope": str,
                "error": Optional[str]
            }
        """
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "client_id": client_id
        }

        from app.core.utils.http_client import get_http_client

        client = await get_http_client()
        try:
            logger.info(f"Exchanging authorization code for token at {token_endpoint}")
            response = await client.post(
                token_endpoint,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                token_data = response.json()

                logger.info("Successfully obtained access token")
                return {
                    "success": True,
                    "access_token": token_data.get('access_token'),
                    "refresh_token": token_data.get('refresh_token'),
                    "token_type": token_data.get('token_type', 'Bearer'),
                    "expires_in": token_data.get('expires_in', 3600),
                    "scope": token_data.get('scope', ''),
                    "error": None
                }
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                logger.error(f"Token exchange failed: {response.status_code} - {error_data}")
                return {
                    "success": False,
                    "access_token": None,
                    "refresh_token": None,
                    "token_type": None,
                    "expires_in": None,
                    "scope": None,
                    "error": error_data.get('error_description', f"HTTP {response.status_code}")
                }

        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return {
                "success": False,
                "access_token": None,
                "refresh_token": None,
                "token_type": None,
                "expires_in": None,
                "scope": None,
                "error": str(e)
                }

    @staticmethod
    async def refresh_token(
        token_endpoint: str,
        refresh_token: str,
        client_id: str
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            token_endpoint: OAuth server token endpoint
            refresh_token: Refresh token
            client_id: Client ID

        Returns:
            {
                "success": bool,
                "access_token": str,
                "refresh_token": str,
                "token_type": str,
                "expires_in": int,
                "error": Optional[str]
            }
        """
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id
        }

        from app.core.utils.http_client import get_http_client

        client = await get_http_client()
        try:
            logger.info(f"Refreshing access token at {token_endpoint}")
            response = await client.post(
                token_endpoint,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code == 200:
                token_data = response.json()

                logger.info("Successfully refreshed access token")
                return {
                    "success": True,
                    "access_token": token_data.get('access_token'),
                    "refresh_token": token_data.get('refresh_token', refresh_token),  # May return same token
                    "token_type": token_data.get('token_type', 'Bearer'),
                    "expires_in": token_data.get('expires_in', 3600),
                    "error": None
                }
            else:
                logger.error(f"Token refresh failed: {response.status_code}")
                return {
                    "success": False,
                    "access_token": None,
                    "refresh_token": None,
                    "token_type": None,
                    "expires_in": None,
                    "error": f"HTTP {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return {
                "success": False,
                "access_token": None,
                "refresh_token": None,
                "token_type": None,
                "expires_in": None,
                "error": str(e)
            }

    # ===== SESSIONS =====

    @staticmethod
    async def store_session(
        server_id: str,
        state: str,
        code_verifier: str,
        code_challenge: str,
        redirect_uri: str,
        scope: Optional[str] = None
    ) -> str:
        """
        Store OAuth session awaiting authorization.

        Args:
            server_id: MCP server ID
            state: Generated state for CSRF protection
            code_verifier: PKCE code verifier
            code_challenge: PKCE code challenge
            redirect_uri: Callback URI
            scope: Requested scopes

        Returns:
            session_id: Created session ID
        """
        conn = await get_connection()
        try:
            session_id = await conn.fetchval("""
                INSERT INTO oauth_sessions (
                    server_id, state, code_verifier, code_challenge, redirect_uri, scope
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, server_id, state, code_verifier, code_challenge, redirect_uri, scope)

            logger.info(f"Stored OAuth session for server {server_id}")
            return session_id

        finally:
            await conn.close()

    @staticmethod
    async def get_session(state: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve OAuth session by state.

        Args:
            state: OAuth state

        Returns:
            Session dict or None if not found/expired
        """
        conn = await get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT id, server_id, state, code_verifier, code_challenge,
                       redirect_uri, scope, created_at, expires_at
                FROM oauth_sessions
                WHERE state = $1 AND expires_at > NOW()
            """, state)

            if row:
                return dict(row)
            return None

        finally:
            await conn.close()

    @staticmethod
    async def delete_session(session_id: str) -> bool:
        """
        Delete OAuth session after use.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False otherwise
        """
        conn = await get_connection()
        try:
            result = await conn.execute("""
                DELETE FROM oauth_sessions
                WHERE id = $1
            """, session_id)

            deleted = result.split()[-1] == '1'
            if deleted:
                logger.info(f"Deleted OAuth session {session_id}")
            return deleted

        finally:
            await conn.close()

    @staticmethod
    async def cleanup_expired_sessions():
        """Clean up expired OAuth sessions."""
        conn = await get_connection()
        try:
            result = await conn.execute("""
                DELETE FROM oauth_sessions
                WHERE expires_at < NOW()
            """)

            count = int(result.split()[-1])
            if count > 0:
                logger.info(f"Cleaned up {count} expired OAuth sessions")

        finally:
            await conn.close()

    # ===== TOKENS =====

    @staticmethod
    async def store_tokens(
        server_id: str,
        access_token: str,
        refresh_token: Optional[str],
        expires_in: int,
        token_type: str = "Bearer",
        scope: Optional[str] = None
    ) -> str:
        """
        Store OAuth tokens for a server.

        Args:
            server_id: MCP server ID
            access_token: Access token
            refresh_token: Refresh token (optional)
            expires_in: Validity duration in seconds
            token_type: Token type (typically "Bearer")
            scope: Granted scopes

        Returns:
            token_id: Created token ID
        """
        conn = await get_connection()
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            # Upsert: if server already exists, update tokens
            token_id = await conn.fetchval("""
                INSERT INTO oauth_tokens (
                    server_id, access_token, refresh_token, token_type, expires_at, scope
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (server_id)
                DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    token_type = EXCLUDED.token_type,
                    expires_at = EXCLUDED.expires_at,
                    scope = EXCLUDED.scope,
                    updated_at = NOW()
                RETURNING id
            """, server_id, access_token, refresh_token, token_type, expires_at, scope)

            logger.info(f"Stored OAuth tokens for server {server_id}")
            return token_id

        finally:
            await conn.close()

    @staticmethod
    async def get_tokens(server_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve OAuth tokens for a server.

        Args:
            server_id: MCP server ID

        Returns:
            Tokens dict or None if not found
        """
        conn = await get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT id, server_id, access_token, refresh_token, token_type,
                       expires_at, scope, created_at, updated_at
                FROM oauth_tokens
                WHERE server_id = $1
            """, server_id)

            if row:
                return dict(row)
            return None

        finally:
            await conn.close()

    @staticmethod
    async def is_expired(server_id: str) -> bool:
        """
        Check if server token is expired.

        Args:
            server_id: MCP server ID

        Returns:
            True if expired or not found, False otherwise
        """
        tokens = await OAuthManager.get_tokens(server_id)

        if not tokens:
            return True

        # Check if expired (with 60 second margin)
        expires_at = tokens['expires_at']
        now = datetime.now(timezone.utc)

        return now >= (expires_at - timedelta(seconds=60))

    @staticmethod
    async def update_tokens(
        server_id: str,
        access_token: str,
        refresh_token: Optional[str],
        expires_in: int
    ) -> bool:
        """
        Update OAuth tokens after refresh.

        Args:
            server_id: MCP server ID
            access_token: New access token
            refresh_token: New refresh token (may be same)
            expires_in: New validity duration in seconds

        Returns:
            True if updated, False otherwise
        """
        conn = await get_connection()
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            result = await conn.execute("""
                UPDATE oauth_tokens
                SET access_token = $1,
                    refresh_token = $2,
                    expires_at = $3,
                    updated_at = NOW()
                WHERE server_id = $4
            """, access_token, refresh_token, expires_at, server_id)

            updated = result.split()[-1] == '1'
            if updated:
                logger.info(f"Updated OAuth tokens for server {server_id}")
            return updated

        finally:
            await conn.close()

    @staticmethod
    async def delete_tokens(server_id: str) -> bool:
        """
        Delete OAuth tokens for a server.

        Args:
            server_id: MCP server ID

        Returns:
            True if deleted, False otherwise
        """
        conn = await get_connection()
        try:
            result = await conn.execute("""
                DELETE FROM oauth_tokens
                WHERE server_id = $1
            """, server_id)

            deleted = result.split()[-1] == '1'
            if deleted:
                logger.info(f"Deleted OAuth tokens for server {server_id}")
            return deleted

        finally:
            await conn.close()
