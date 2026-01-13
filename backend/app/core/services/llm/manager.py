# app/core/services/llm/manager.py
"""
StreamManager - Gestion des sessions de streaming avec validations.

Ce service gère :
- Les sessions de streaming actives
- Les événements de stop (bouton stop utilisateur)
- Les événements de validation (déblocage asynchrone après validation)
- La reprise automatique après validation

Architecture:
- Une session = un chat en cours de streaming
- Chaque session a un stop_event (pour arrêt utilisateur)
- Chaque session a un validation_event (pour déblocage après validation)
- Timeout de 15 jours sur les validations
"""

import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from config.logger import logger


@dataclass
class StreamSession:
    """Représente une session de streaming active."""

    chat_id: str
    user_id: str
    started_at: datetime

    # Événements de contrôle
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    validation_event: asyncio.Event = field(default_factory=asyncio.Event)

    # Résultat de validation (set quand validation_event est déclenché)
    validation_result: Optional[Dict[str, Any]] = None

    # Sources RAG utilisées pour le message en cours (reset à chaque nouveau message)
    sources: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # État
    is_active: bool = True

    # Validation en attente (pour garder session après déconnexion)
    pending_validation_id: Optional[str] = None

    # Date de déconnexion (si stream frontend fermé pendant validation)
    disconnected_at: Optional[datetime] = None

    def reset_sources(self):
        """Reset les sources pour un nouveau message."""
        self.sources.clear()
        logger.debug(f"Sources reset for chat {self.chat_id}")


class StreamManager:
    """
    Gestionnaire global des sessions de streaming.

    Responsabilités:
    - Enregistrer/désinscrire les sessions actives
    - Vérifier si un stream est actif pour un chat
    - Arrêter un stream (stop_event)
    - Débloquer un stream après validation (validation_event)
    """

    def __init__(self):
        self.active_sessions: Dict[str, StreamSession] = {}
        logger.info("StreamManager initialized")

    def start_session(self, chat_id: str, user_id: str) -> StreamSession:
        """
        Démarre une nouvelle session de streaming.

        Args:
            chat_id: ID du chat
            user_id: ID de l'utilisateur

        Returns:
            StreamSession créée

        Note:
            Si une session existe déjà pour ce chat_id, elle sera remplacée.
        """
        # Nettoyer l'ancienne session si existe
        if chat_id in self.active_sessions:
            logger.warning(f"Session already exists for chat {chat_id}, replacing")
            self.end_session(chat_id)

        session = StreamSession(
            chat_id=chat_id,
            user_id=user_id,
            started_at=datetime.now()
        )

        self.active_sessions[chat_id] = session

        logger.info(f"Stream session started: chat={chat_id}, user={user_id}")

        return session

    def get_session(self, chat_id: str) -> Optional[StreamSession]:
        """
        Récupère une session active.

        Args:
            chat_id: ID du chat

        Returns:
            StreamSession si active, None sinon
        """
        return self.active_sessions.get(chat_id)

    def is_stream_active(self, chat_id: str) -> bool:
        """
        Vérifie si un stream est actif pour un chat OU attend une validation.

        Une session déconnectée mais avec pending_validation_id est considérée active.
        Cela permet l'injection de résultat même si l'utilisateur a quitté le chat.

        Args:
            chat_id: ID du chat

        Returns:
            True si session active OU session déconnectée avec validation pending
        """
        session = self.get_session(chat_id)
        if not session:
            return False

        # Si actif, OK
        if session.is_active:
            return True

        # Si déconnecté MAIS validation en attente → considérer comme actif
        if session.pending_validation_id:
            return True

        return False

    def stop_stream(self, chat_id: str) -> bool:
        """
        Demande l'arrêt d'un stream (bouton stop utilisateur).

        Args:
            chat_id: ID du chat

        Returns:
            True si le stop a été déclenché, False si pas de session

        Side effects:
            Set le stop_event de la session, ce qui provoque l'arrêt du stream
        """
        session = self.get_session(chat_id)

        if not session:
            logger.warning(f"Cannot stop stream: no active session for chat {chat_id}")
            return False

        session.stop_event.set()
        logger.info(f"Stop requested for chat {chat_id}")

        return True

    async def inject_validation_result(
        self,
        chat_id: str,
        validation_result: Dict[str, Any]
    ) -> bool:
        """
        Injecte un résultat de validation dans un stream actif.

        Args:
            chat_id: ID du chat
            validation_result: Résultat de la validation
                {
                    "validation_id": str,
                    "action": "approved" | "rejected" | "feedback",
                    "data": Any  # Résultat d'exécution du tool si approved
                }

        Returns:
            True si injection réussie, False si pas de session active

        Side effects:
            - Set validation_result sur la session
            - Déclenche validation_event pour débloquer le stream
        """
        session = self.get_session(chat_id)

        if not session:
            logger.warning(f"Cannot inject validation: no active session for chat {chat_id}")
            return False

        session.validation_result = validation_result
        session.validation_event.set()

        logger.info(
            f"Validation result injected: chat={chat_id}, "
            f"validation_id={validation_result.get('validation_id')}, "
            f"action={validation_result.get('action')}"
        )

        return True

    def reset_validation_event(self, chat_id: str):
        """
        Reset l'événement de validation (pour gérer plusieurs validations dans un même stream).

        Args:
            chat_id: ID du chat

        Note:
            À appeler après avoir consommé le résultat de validation,
            pour préparer la prochaine validation potentielle.
        """
        session = self.get_session(chat_id)

        if session:
            session.validation_event.clear()
            session.validation_result = None
            logger.debug(f"Validation event reset for chat {chat_id}")

    def end_session(self, chat_id: str):
        """
        Termine et nettoie une session.

        Args:
            chat_id: ID du chat

        Note:
            À appeler quand le stream se termine (normalement ou par erreur)
        """
        session = self.active_sessions.pop(chat_id, None)

        if session:
            session.is_active = False
            duration = (datetime.now() - session.started_at).total_seconds()

            logger.info(
                f"Stream session ended: chat={chat_id}, duration={duration:.1f}s"
            )
        else:
            logger.debug(f"No session to end for chat {chat_id}")

    async def cleanup_inactive_sessions(self, max_age_seconds: int = 3600):
        """
        Nettoie les sessions inactives :
        - Déconnectées avec validation expirée/résolue (> 48h ou status != pending)
        - Actives trop vieilles (> max_age_seconds)

        Args:
            max_age_seconds: Âge maximum en secondes (défaut: 1h)

        Note:
            À appeler périodiquement (ex: via scheduler)
            Maintenant async pour vérifier le statut des validations en DB
        """
        from app.database import crud  # Import local pour éviter circular
        now = datetime.now()
        to_remove = []

        for chat_id, session in self.active_sessions.items():
            # Si validation en attente, vérifier son statut en DB
            if session.pending_validation_id:
                try:
                    validation = await crud.get_validation(session.pending_validation_id)
                    if validation:
                        status = validation.get('status')
                        # Supprimer si validation résolue ou expirée
                        if status in ('approved', 'rejected', 'cancelled', 'feedback'):
                            to_remove.append(chat_id)
                            logger.info(f"Cleaning session {chat_id}: validation {status}")
                            continue
                except Exception as e:
                    logger.error(f"Error checking validation {session.pending_validation_id}: {e}")

            # Si déconnectée sans validation, supprimer immédiatement
            if session.disconnected_at and not session.pending_validation_id:
                to_remove.append(chat_id)
                continue

            # Nettoyage des sessions normales trop vieilles (sans validation pending)
            age = (now - session.started_at).total_seconds()
            if age > max_age_seconds and not session.pending_validation_id:
                to_remove.append(chat_id)

        for chat_id in to_remove:
            logger.warning(f"Cleaning up session: chat={chat_id}")
            self.end_session(chat_id)

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} stale session(s)")

    def get_active_session_count(self) -> int:
        """Retourne le nombre de sessions actives."""
        return len(self.active_sessions)

    def get_session_info(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les infos d'une session.

        Args:
            chat_id: ID du chat

        Returns:
            Dict avec infos de la session ou None
        """
        session = self.get_session(chat_id)

        if not session:
            return None

        return {
            "chat_id": session.chat_id,
            "user_id": session.user_id,
            "started_at": session.started_at.isoformat(),
            "is_active": session.is_active,
            "stop_requested": session.stop_event.is_set(),
            "waiting_validation": not session.validation_event.is_set() and session.validation_result is None,
            "uptime_seconds": (datetime.now() - session.started_at).total_seconds()
        }


# Instance globale réutilisable
stream_manager = StreamManager()
