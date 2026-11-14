"""Affiche les skills trouvés et leur coût en tokens (outil de vérification)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from registry.parser import SkillError, discover_skills, parse_skill_file  # noqa: E402

skills, errors = [], []
for path in discover_skills(ROOT / "departments"):
    try:
        skills.append(parse_skill_file(path))
    except SkillError as exc:
        errors.append(str(exc))

for s in skills:
    print(
        f"{s.department:<11} {s.subdomain:<16} {s.meta.name:<22} "
        f"index={s.meta_tokens:>3} corps={s.body_tokens:>4} outils={','.join(s.meta.allowed_tools)}"
    )
    for w in s.warnings:
        print(f"   AVERTISSEMENT : {w}")

print()
print(f"{len(skills)} skills valides, {len(errors)} erreurs")
for e in errors:
    print(f"   ERREUR : {e}")
print(f"Niveau 1 (index de tous les skills) : {sum(s.meta_tokens for s in skills)} tokens")
print(f"Niveau 2 (tous les corps)           : {sum(s.body_tokens for s in skills)} tokens")
sys.exit(1 if errors else 0)