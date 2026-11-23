"""Garde : décide si l'IA a le droit d'appeler un outil. Les vérifications, dans l'ordre :

    skill_not_active       aucun skill n'est actif
    tool_not_allowed       l'outil n'appartient à aucun skill actif
    bad_arguments          argument inconnu, manquant, mauvais type ou valeur interdite
    confirmation_required  outil d'écriture sans confirmation de l'utilisateur
    ok                     appel autorisé
"""

from dataclasses import dataclass

from registry.models import Tool

TYPES = {"string": str, "number": (int, float), "integer": int, "boolean": bool}


@dataclass
class Decision:
    allowed: bool
    code: str
    message: str


def argument_problem(arguments: dict, parameters: list) -> str:
    """Compare les arguments à la définition de l'outil (tools/*.yaml). Retourne "" si tout va bien."""
    names = [p["name"] for p in parameters]
    for name in arguments:
        if name not in names:
            return f"argument inconnu : {name}"
    for p in parameters:
        if p["name"] not in arguments:
            if p.get("required"):
                return f"argument obligatoire manquant : {p['name']}"
            continue
        value = arguments[p["name"]]
        wrong_bool = isinstance(value, bool) and p["type"] != "boolean"
        if not isinstance(value, TYPES[p["type"]]) or wrong_bool:
            return f"{p['name']} doit être de type {p['type']}"
        if p.get("enum") and value not in p["enum"]:
            return f"{p['name']} doit valoir {' ou '.join(p['enum'])}"
    return ""


def check_tool_call(tool: str, arguments: dict, context, confirmed: bool = False) -> Decision:
    """context : le CompileResult utilisé pour cette étape (skills actifs, outils autorisés)."""
    if not context.active_skills:
        return Decision(False, "skill_not_active", "activez un skill avant d'appeler un outil")
    if tool not in context.allowed_tools:
        return Decision(False, "tool_not_allowed", f"l'outil {tool} n'est pas autorisé par les skills actifs")
    definition = Tool.objects.filter(name=tool).first()
    if definition is None:
        return Decision(False, "tool_not_allowed", f"l'outil {tool} n'existe pas")
    problem = argument_problem(arguments, definition.parameters)
    if problem:
        return Decision(False, "bad_arguments", problem)
    if definition.mode == "write" and not confirmed:
        return Decision(False, "confirmation_required",
                        f"{tool} modifie des données : l'utilisateur doit d'abord confirmer")
    return Decision(True, "ok", "appel autorisé")
