import secrets
import string
from typing import Literal

# Définition des types d'IDs possibles
IDType = Literal[
    'user', 'reset_token', 'agent', 'upload', 'team', 'membership',
    'chat', 'message', 'validation', 'resource', 'server', 'tool', 'configuration', 'key',
    'service', 'model', 'user_provider', 'log',
    'automation', 'workflow_step', 'trigger', 'execution', 'execution_step_log'
]

# Mapping type -> préfixe (3 lettres)
ID_PREFIXES = {
    'user': 'usr',
    'reset_token': 'rst',
    'agent': 'agt',
    'upload': 'upl',
    'team': 'tem',
    'membership': 'mbr',
    'chat': 'cht',
    'message': 'msg',
    'validation': 'val',
    'resource': 'res',
    'server': 'srv',
    'tool': 'tol',
    'configuration': 'cfg',
    'key': 'key',
    'service': 'svc',
    'model': 'mdl',
    'user_provider': 'upr',
    'log': 'log',
    'automation': 'auto',
    'workflow_step': 'step',
    'trigger': 'trg',
    'execution': 'exec',
    'execution_step_log': 'esl'
}

# Patterns de validation (regex)
ID_PATTERNS = {
    'user': r'^usr_[A-Za-z0-9]{6,}$',
    'reset_token': r'^rst_[A-Za-z0-9]{6,}$',
    'agent': r'^agt_[A-Za-z0-9]{6,}$',
    'upload': r'^upl_[A-Za-z0-9]{6,}$',
    'team': r'^tem_[A-Za-z0-9]{6,}$',
    'membership': r'^mbr_[A-Za-z0-9]{6,}$',
    'chat': r'^cht_[A-Za-z0-9]{6,}$',
    'message': r'^msg_[A-Za-z0-9]{6,}$',
    'validation': r'^val_[A-Za-z0-9]{6,}$',
    'resource': r'^res_[A-Za-z0-9]{6,}$',
    'server': r'^srv_[A-Za-z0-9]{6,}$',
    'tool': r'^tol_[A-Za-z0-9]{6,}$',
    'configuration': r'^cfg_[A-Za-z0-9]{6,}$',
    'key': r'^key_[A-Za-z0-9]{6,}$',
    'service': r'^svc_[A-Za-z0-9]{6,}$',
    'model': r'^mdl_[A-Za-z0-9]{6,}$',
    'user_provider': r'^upr_[A-Za-z0-9]{6,}$',
    'log': r'^log_[A-Za-z0-9]{6,}$',
    'automation': r'^auto_[A-Za-z0-9]{6,}$',
    'workflow_step': r'^step_[A-Za-z0-9]{6,}$',
    'trigger': r'^trg_[A-Za-z0-9]{6,}$',
    'execution': r'^exec_[A-Za-z0-9]{6,}$',
    'execution_step_log': r'^esl_[A-Za-z0-9]{6,}$'
}

def generate_id(id_type: IDType, length: int = 6) -> str:
    """
    Génère un ID sécurisé avec préfixe.

    Args:
        id_type: Type d'ID à générer (voir IDType)
        length: Longueur de la partie aléatoire (default: 6)

    Returns:
        ID au format: {prefix}_{random}
        Exemple: usr_Kx9mP2

    Raises:
        ValueError: Si id_type invalide
    """
    if id_type not in ID_PREFIXES:
        raise ValueError(f"Invalid id_type: {id_type}. Must be one of {list(ID_PREFIXES.keys())}")

    prefix = ID_PREFIXES[id_type]
    chars = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    random_part = ''.join(secrets.choice(chars) for _ in range(length))

    return f"{prefix}_{random_part}"

def is_valid_id(id_value: str, id_type: IDType) -> bool:
    """
    Valide qu'un ID correspond au format attendu pour son type.

    Args:
        id_value: L'ID à valider
        id_type: Le type d'ID attendu

    Returns:
        True si valide, False sinon
    """
    import re

    if id_type not in ID_PATTERNS:
        return False

    pattern = ID_PATTERNS[id_type]
    return bool(re.match(pattern, id_value))

def get_prefix(id_type: IDType) -> str:
    """
    Retourne le préfixe pour un type d'ID donné.

    Args:
        id_type: Type d'ID

    Returns:
        Préfixe (3 lettres)
    """
    return ID_PREFIXES.get(id_type, '')

def extract_type_from_id(id_value: str) -> str | None:
    """
    Extrait le type d'ID depuis sa valeur (via le préfixe).

    Args:
        id_value: ID complet (ex: usr_Kx9mP2)

    Returns:
        Type d'ID ou None si invalide
    """
    if '_' not in id_value:
        return None

    prefix = id_value.split('_')[0]

    for id_type, type_prefix in ID_PREFIXES.items():
        if type_prefix == prefix:
            return id_type

    return None
