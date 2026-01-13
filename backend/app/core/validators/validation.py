#!/usr/bin/env python3
# app/core/validators/validation.py
"""
Validators métier pour les validations.

Gère les règles métier spécifiques aux validations:
- Transitions de statut autorisées
- Vérification ownership
- Vérification statut pending pour actions
"""

from typing import Optional
from app.core.validators.base import BaseValidator
from app.core.exceptions import ValidationError, NotFoundError, PermissionError
from app.database.models import Validation


class ValidationValidator(BaseValidator):
    """Validateurs métier pour les validations."""

    # Matrice de transitions autorisées
    # Une fois en statut final (approved/rejected/cancelled), le statut ne peut plus changer
    ALLOWED_TRANSITIONS = {
        'pending': ['approved', 'rejected', 'feedback', 'cancelled'],
        'feedback': ['approved', 'rejected', 'cancelled'],
        'approved': [],  # IMMUTABLE (statut final)
        'rejected': [],  # IMMUTABLE (statut final)
        'cancelled': []  # IMMUTABLE (statut final)
    }

    @staticmethod
    async def validate_status_transition(
        current_status: str,
        new_status: str
    ) -> None:
        """
        Valide qu'une transition de statut est autorisée selon ALLOWED_TRANSITIONS.

        Args:
            current_status: Statut actuel de la validation
            new_status: Statut cible souhaité

        Raises:
            ValidationError: Si la transition n'est pas autorisée

        Examples:
            >>> await ValidationValidator.validate_status_transition('pending', 'approved')
            # OK

            >>> await ValidationValidator.validate_status_transition('approved', 'rejected')
            # Raises ValidationError: "Cannot change status from 'approved' (immutable final state)"

            >>> await ValidationValidator.validate_status_transition('pending', 'completed')
            # Raises ValidationError: "Invalid status transition: 'pending' → 'completed'. Allowed: approved, rejected, feedback, cancelled"
        """
        allowed = ValidationValidator.ALLOWED_TRANSITIONS.get(current_status, [])

        if new_status not in allowed:
            # Si liste vide = statut final immutable
            if not allowed:
                raise ValidationError(
                    f"Cannot change status from '{current_status}' (immutable final state)"
                )

            # Sinon = transition non autorisée
            raise ValidationError(
                f"Invalid status transition: '{current_status}' → '{new_status}'. "
                f"Allowed: {', '.join(allowed)}"
            )

    @staticmethod
    async def check_validation_ownership(
        validation_id: str,
        user_id: str
    ) -> Validation:
        """
        Vérifie qu'une validation appartient bien à l'utilisateur.

        Args:
            validation_id: ID de la validation
            user_id: ID de l'utilisateur

        Returns:
            Validation object si OK

        Raises:
            NotFoundError: Si la validation n'existe pas
            PermissionError: Si l'utilisateur n'est pas propriétaire

        Examples:
            >>> validation = await ValidationValidator.check_validation_ownership('val_123', 'user_456')
            # Returns Validation object

            >>> await ValidationValidator.check_validation_ownership('val_999', 'user_456')
            # Raises NotFoundError: "Validation not found"

            >>> await ValidationValidator.check_validation_ownership('val_123', 'user_999')
            # Raises PermissionError: "You don't have permission to access this validation"
        """
        from app.database import crud

        # 1. Récupérer la validation
        validation_row = await crud.get_validation(validation_id)

        if not validation_row:
            raise NotFoundError("Validation not found")

        # 2. Convertir en modèle
        validation = Validation.from_row(validation_row)

        # 3. Vérifier ownership
        if validation.user_id != user_id:
            raise PermissionError("You don't have permission to access this validation")

        return validation

    @staticmethod
    async def ensure_validation_pending(validation: Validation) -> None:
        """
        Vérifie qu'une validation est en statut 'pending'.

        Cette vérification est nécessaire avant approve/reject/feedback car ces actions
        ne peuvent être effectuées que sur des validations pending.

        Args:
            validation: Objet Validation à vérifier

        Raises:
            ValidationError: Si le statut n'est pas 'pending'

        Examples:
            >>> validation = Validation(status='pending', ...)
            >>> await ValidationValidator.ensure_validation_pending(validation)
            # OK

            >>> validation = Validation(status='approved', ...)
            >>> await ValidationValidator.ensure_validation_pending(validation)
            # Raises ValidationError: "Validation is already approved. Only pending validations can be approved/rejected/feedback."
        """
        if validation.status != 'pending':
            raise ValidationError(
                f"Validation is already {validation.status}. "
                f"Only pending validations can be approved/rejected/feedback."
            )
