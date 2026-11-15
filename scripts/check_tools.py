"""Valide le catalogue d'outils et affiche les permissions qui en découlent."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from registry.tools import known_departments, load_catalog  # noqa: E402

departments = known_departments(ROOT / "departments")
catalog = load_catalog(ROOT / "tools", departments)

for error in catalog.errors:
    print(f"ERREUR : {error}")
print(f"{len(catalog.tools)} outils définis, {len(catalog.errors)} erreurs")
print()
print("Permissions dérivées du catalogue :")
for dept in sorted(departments):
    allowed = [t for t in catalog.tools.values() if dept in t.departments]
    writes = sorted(t.name for t in allowed if t.mode == "write")
    print(f"  {dept:<11} {len(allowed):>2} outils autorisés, dont écriture : {', '.join(writes) or 'aucun'}")
sys.exit(1 if catalog.errors else 0)