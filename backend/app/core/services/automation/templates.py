"""
Module de résolution de templates sécurisé pour l'automatisation.

Fournit des fonctions pour :
- Naviguer dans des structures de données imbriquées
- Résoudre des templates {{...}} avec contexte
- Évaluer des expressions conditionnelles de manière sécurisée (AST parsing)
"""

import ast
import re
from typing import Any, Dict, List, Union


def get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """
    Récupère une valeur dans un dict imbriqué en suivant un chemin.

    Supporte :
    - Navigation dans les dicts : "a.b.c"
    - Accès aux listes par index : "items.0.name"

    Args:
        data: Dictionnaire source
        path: Chemin séparé par des points (ex: "step_0.result.temp")

    Returns:
        La valeur trouvée ou None si le chemin n'existe pas

    Examples:
        >>> data = {"step_0": {"result": {"temp": 30}}}
        >>> get_nested_value(data, "step_0.result.temp")
        30

        >>> data = {"items": [{"name": "foo"}, {"name": "bar"}]}
        >>> get_nested_value(data, "items.1.name")
        'bar'

        >>> get_nested_value(data, "nonexistent.path")
        None
    """
    if not path:
        return data

    parts = path.split(".")
    current = data

    for part in parts:
        if current is None:
            return None

        # Vérifier si c'est un index de liste
        if isinstance(current, list):
            try:
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None

    return current


def resolve_template(template: str, context: Dict[str, Any]) -> Any:
    """
    Résout un template avec le contexte fourni.

    Comportement :
    - Si template = exactement "{{path}}" → retourne la valeur brute (dict/list/int/str/etc.)
    - Sinon → fait du remplacement de string et retourne une string

    Args:
        template: String contenant des {{path}} à résoudre
        context: Dictionnaire de contexte pour la résolution

    Returns:
        Valeur résolue (type préservé si template simple, sinon string)

    Examples:
        >>> context = {"step_0": {"result": {"temp": 30}}}
        >>> resolve_template("{{step_0.result.temp}}", context)
        30

        >>> resolve_template("Temperature: {{step_0.result.temp}}°C", context)
        'Temperature: 30°C'

        >>> resolve_template("No template here", context)
        'No template here'
    """
    # Pattern pour détecter {{...}}
    pattern = re.compile(r'\{\{([^}]+)\}\}')

    # Vérifier si c'est exactement un template simple
    match = pattern.fullmatch(template.strip())
    if match:
        # Template simple : retourner la valeur brute
        path = match.group(1).strip()
        return get_nested_value(context, path)

    # Template complexe : faire du string replacement
    def replace_match(match):
        path = match.group(1).strip()
        value = get_nested_value(context, path)
        return str(value) if value is not None else ""

    return pattern.sub(replace_match, template)


def resolve_all_templates(obj: Any, context: Dict[str, Any]) -> Any:
    """
    Résout récursivement tous les templates dans une structure de données.

    Parcourt :
    - Strings : résout les templates
    - Dicts : applique récursivement sur chaque valeur
    - Lists : applique récursivement sur chaque item
    - Autres types : retourne tel quel

    Args:
        obj: Objet à traiter (peut être n'importe quel type)
        context: Dictionnaire de contexte pour la résolution

    Returns:
        Objet avec tous les templates résolus

    Examples:
        >>> context = {"step_0": {"result": {"temp": 30}}}
        >>> obj = {
        ...     "message": "Temp is {{step_0.result.temp}}°C",
        ...     "value": "{{step_0.result.temp}}",
        ...     "nested": {"data": "{{step_0.result}}"}
        ... }
        >>> resolve_all_templates(obj, context)
        {
            'message': 'Temp is 30°C',
            'value': 30,
            'nested': {'data': {'temp': 30}}
        }
    """
    if isinstance(obj, str):
        return resolve_template(obj, context)
    elif isinstance(obj, dict):
        return {key: resolve_all_templates(value, context) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [resolve_all_templates(item, context) for item in obj]
    else:
        return obj


def evaluate_expression(expression: str) -> bool:
    """
    Évalue une expression booléenne de manière sécurisée via AST parsing.

    Opérations supportées :
    - Comparaisons : >, <, ==, !=, >=, <=
    - Opérateurs booléens : and, or, not
    - Opérateurs d'appartenance : in, not in
    - Listes : [1, 2, 3]
    - Constants : True, False, None, nombres, strings

    NE PAS utiliser eval() pour des raisons de sécurité.

    Args:
        expression: Expression à évaluer (ex: "30 > 25", "x in [1, 2, 3]")

    Returns:
        Résultat booléen de l'évaluation

    Raises:
        ValueError: Si l'expression contient des opérations non autorisées

    Examples:
        >>> evaluate_expression("30 > 25")
        True

        >>> evaluate_expression("10 < 5")
        False

        >>> evaluate_expression("'foo' in ['foo', 'bar']")
        True

        >>> evaluate_expression("(5 > 3) and (10 < 20)")
        True

        >>> evaluate_expression("not (5 > 10)")
        True
    """
    try:
        # Parser l'expression en AST
        tree = ast.parse(expression, mode='eval')

        def eval_node(node):
            """Évalue récursivement un noeud AST."""
            if isinstance(node, ast.Constant):
                # Python 3.8+ : Constant pour tous les littéraux
                return node.value
            elif isinstance(node, ast.Num):
                # Rétrocompatibilité Python 3.7
                return node.n
            elif isinstance(node, ast.Str):
                # Rétrocompatibilité Python 3.7
                return node.s
            elif isinstance(node, ast.NameConstant):
                # Rétrocompatibilité Python 3.7 (True, False, None)
                return node.value
            elif isinstance(node, ast.List):
                return [eval_node(item) for item in node.elts]
            elif isinstance(node, ast.Tuple):
                return tuple(eval_node(item) for item in node.elts)
            elif isinstance(node, ast.Compare):
                # Comparaison : left op comparators
                left = eval_node(node.left)
                result = True

                for op, comparator in zip(node.ops, node.comparators):
                    right = eval_node(comparator)

                    if isinstance(op, ast.Gt):
                        result = result and (left > right)
                    elif isinstance(op, ast.Lt):
                        result = result and (left < right)
                    elif isinstance(op, ast.GtE):
                        result = result and (left >= right)
                    elif isinstance(op, ast.LtE):
                        result = result and (left <= right)
                    elif isinstance(op, ast.Eq):
                        result = result and (left == right)
                    elif isinstance(op, ast.NotEq):
                        result = result and (left != right)
                    elif isinstance(op, ast.In):
                        result = result and (left in right)
                    elif isinstance(op, ast.NotIn):
                        result = result and (left not in right)
                    else:
                        raise ValueError(f"Opérateur de comparaison non supporté : {op.__class__.__name__}")

                    left = right

                return result
            elif isinstance(node, ast.BoolOp):
                # Opérateurs booléens : and, or
                if isinstance(node.op, ast.And):
                    return all(eval_node(value) for value in node.values)
                elif isinstance(node.op, ast.Or):
                    return any(eval_node(value) for value in node.values)
                else:
                    raise ValueError(f"Opérateur booléen non supporté : {node.op.__class__.__name__}")
            elif isinstance(node, ast.UnaryOp):
                # Opérateurs unaires : not
                if isinstance(node.op, ast.Not):
                    return not eval_node(node.operand)
                else:
                    raise ValueError(f"Opérateur unaire non supporté : {node.op.__class__.__name__}")
            elif isinstance(node, ast.Expression):
                return eval_node(node.body)
            else:
                raise ValueError(f"Type de noeud non supporté : {node.__class__.__name__}")

        result = eval_node(tree)

        # Assurer que le résultat est un booléen
        if not isinstance(result, bool):
            raise ValueError(f"L'expression doit retourner un booléen, pas {type(result).__name__}")

        return result

    except SyntaxError as e:
        raise ValueError(f"Erreur de syntaxe dans l'expression : {e}")
    except Exception as e:
        raise ValueError(f"Erreur lors de l'évaluation de l'expression : {e}")


def evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
    """
    Résout les templates dans une condition puis l'évalue.

    Combine resolve_template() et evaluate_expression() pour permettre
    l'évaluation de conditions avec des variables du contexte.

    Args:
        condition: Condition avec templates (ex: "{{step_0.result.temp}} > 25")
        context: Dictionnaire de contexte pour la résolution

    Returns:
        Résultat booléen de la condition évaluée

    Raises:
        ValueError: Si la condition est invalide ou mal formée

    Examples:
        >>> context = {"step_0": {"result": {"temp": 30}}}
        >>> evaluate_condition("{{step_0.result.temp}} > 25", context)
        True

        >>> context = {"status": "success"}
        >>> evaluate_condition("'{{status}}' == 'success'", context)
        True

        >>> context = {"count": 5, "limit": 10}
        >>> evaluate_condition("{{count}} < {{limit}}", context)
        True
    """
    # Résoudre les templates dans la condition
    resolved = resolve_template(condition, context)

    # Si la résolution a donné une string, l'évaluer
    if isinstance(resolved, str):
        return evaluate_expression(resolved)
    elif isinstance(resolved, bool):
        # Si c'est déjà un booléen (cas rare), le retourner
        return resolved
    else:
        raise ValueError(f"La condition résolue doit être une expression évaluable, pas {type(resolved).__name__}")
