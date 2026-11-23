"""Exécuteur : appelle la vraie fonction Python de l'outil (erp/tools.py).

La garde (engine/guard.py) a déjà vérifié le skill actif, les arguments et la confirmation.
Le résultat est renvoyé en JSON : c'est l'« observation » que l'IA lira à l'étape suivante.
Une erreur normale (ex. facture introuvable) est aussi renvoyée à l'IA, comme un texte.
"""

import json

from erp.tools import TOOLS, ToolError


def execute_tool(tool: str, arguments: dict) -> str:
    function = TOOLS.get(tool)
    if function is None:
        return f"Erreur de l'outil : {tool} n'a pas d'implémentation"
    try:
        result = function(**arguments)
    except ToolError as exc:
        return f"Erreur de l'outil {tool} : {exc}"
    return json.dumps(result, ensure_ascii=False, indent=1)
