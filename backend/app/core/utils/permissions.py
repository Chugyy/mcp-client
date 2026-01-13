"""Utilitaires de gestion des permissions."""

from typing import Dict
from app.database.models import User


def is_super_admin(user: User) -> bool:
    """
    Vérifie si un utilisateur est super-admin (système).

    Les super-admins ont accès à toutes les ressources du système.

    Args:
        user: L'utilisateur à vérifier

    Returns:
        True si l'utilisateur est super-admin, False sinon
    """
    return getattr(user, 'is_system', False)


def can_access_automation(user: User, automation: Dict) -> bool:
    """
    Vérifie si un utilisateur peut accéder à une automation.

    Un utilisateur peut accéder à une automation si :
    - Il est super-admin (is_system = true)
    - L'automation est système (is_system = true)
    - Il est le propriétaire de l'automation (user_id correspond)

    Args:
        user: L'utilisateur qui tente d'accéder
        automation: Dictionnaire contenant les informations de l'automation

    Returns:
        True si l'accès est autorisé, False sinon
    """
    # Super-admins ont accès à tout
    if is_super_admin(user):
        return True

    # Automations système sont accessibles à tous
    if automation.get("is_system", False):
        return True

    # L'utilisateur doit être le propriétaire
    return automation.get("user_id") == user.id
