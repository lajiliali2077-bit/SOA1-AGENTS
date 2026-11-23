"""Exécuteur : les outils sont simulés avec des réponses prêtes dans fixtures/<département>.json.

Format :
    "get_vendor": [
        {"when": {"vendor_id": "V-00118"}, "output": {...}},   <- si les arguments correspondent
        {"output": "Vendor not found."}                       <- cas par défaut
    ]
"""

import json

from django.conf import settings


def execute_tool(department: str, tool: str, arguments: dict) -> str:
    path = settings.BASE_DIR / "fixtures" / f"{department}.json"
    if not path.is_file():
        raise ValueError(f"pas de fixtures pour le département {department}")
    cases = json.loads(path.read_text(encoding="utf-8")).get(tool)
    if cases is None:
        raise ValueError(f"pas de fixture pour l'outil {tool}")

    for case in cases:
        when = case.get("when", {})
        if all(arguments.get(key) == value for key, value in when.items()):
            output = case["output"]
            return output if isinstance(output, str) else json.dumps(output, ensure_ascii=False, indent=2)
    raise ValueError(f"aucune fixture de {tool} ne correspond à {arguments}")
