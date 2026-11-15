"""Mesure en tokens chaque fichier d'un département.
Usage : python scripts/measure_dept.py finance
"""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from registry.parser import count_tokens  # noqa: E402

if len(sys.argv) != 2:
    sys.exit("Usage : python scripts/measure_dept.py <département>")

dept = sys.argv[1]
base = ROOT / "departments" / dept
if not base.is_dir():
    sys.exit(f"Département introuvable : {base}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


total = 0
print(f"{'Fichier (relatif à departments/' + dept + ')':<78}{'tokens':>8}")
for path in sorted(base.rglob("*.md")):
    tokens = count_tokens(read(path))
    total += tokens
    print(f"{path.relative_to(base).as_posix():<78}{tokens:>8}")
print(f"{'Sous-total Markdown':<78}{total:>8}")

tools_file = ROOT / "tools" / f"{dept}.yaml"
if tools_file.exists():
    tools = yaml.safe_load(read(tools_file)) or []
    tool_tokens = sum(count_tokens(json.dumps(t, ensure_ascii=False)) for t in tools)
    print(f"{f'Outils (tools/{dept}.yaml) : {len(tools)} définitions':<78}{tool_tokens:>8}")
    total += tool_tokens
else:
    print(f"{f'Outils : tools/{dept}.yaml absent':<78}{'-':>8}")
print(f"{'TOTAL du département':<78}{total:>8}")