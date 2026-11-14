"""Mesure la taille du corpus (en tokens) par catégorie."""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from registry.parser import count_tokens  # noqa: E402


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


rows: dict[str, list[int]] = {}


def add(category: str, tokens: int) -> None:
    rows.setdefault(category, []).append(tokens)


departments = ROOT / "departments"

if (ROOT / "AGENTS.md").exists():
    add("AGENTS.md niveau 1", count_tokens(read(ROOT / "AGENTS.md")))
for path in sorted(departments.rglob("AGENTS.md")):
    depth = len(path.relative_to(departments).parts)  # 2 = département, 3 = sous-domaine
    add("AGENTS.md niveau 2" if depth == 2 else "AGENTS.md niveau 3", count_tokens(read(path)))
for path in sorted(departments.rglob("SKILL.md")):
    add("SKILL.md (frontmatter + corps)", count_tokens(read(path)))
for path in sorted(departments.rglob("*.md")):
    if "references" in path.parts:
        add("references/ (niveau 3 des skills)", count_tokens(read(path)))
for path in sorted((ROOT / "tools").glob("*.yaml")):
    for tool in yaml.safe_load(read(path)) or []:
        add("définitions d'outils", count_tokens(json.dumps(tool, ensure_ascii=False)))

ORDER = [
    "AGENTS.md niveau 1",
    "AGENTS.md niveau 2",
    "AGENTS.md niveau 3",
    "SKILL.md (frontmatter + corps)",
    "references/ (niveau 3 des skills)",
    "définitions d'outils",
]

print(f"{'Catégorie':<36}{'éléments':>9}{'tokens':>9}{'moyenne':>9}")
total = 0
for category in ORDER:
    values = rows.get(category)
    if not values:
        continue
    total += sum(values)
    print(f"{category:<36}{len(values):>9}{sum(values):>9}{sum(values) // len(values):>9}")
print(f"{'TOTAL (prompt monolithique)':<36}{'':>9}{total:>9}")