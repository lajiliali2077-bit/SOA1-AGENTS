"""Valide tous les skills contre le catalogue d'outils.
Usage : python scripts/validate_skills.py [--verbose]   (--verbose affiche aussi les infos)
"""

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from registry.validation import (  # noqa: E402
    ACTIVE, INFO, NEEDS_REVIEW, REJECTED, validate_all,
)

verbose = "--verbose" in sys.argv
result = validate_all(ROOT / "departments", ROOT / "tools")

for error in result.catalog.errors:
    print(f"ERREUR CATALOGUE : {error}")

LABEL = {"error": "ERREUR", "warning": "AVERT.", "info": "info  "}
for report in result.reports:
    print(f"[{report.status:<12}] {report.department}/{report.subdomain}/{report.name}")
    for issue in report.issues:
        if issue.severity == INFO and not verbose:
            continue
        print(f"      {LABEL[issue.severity]} {issue.code} : {issue.message}")

counts = Counter(report.status for report in result.reports)
print()
print(
    f"{len(result.reports)} skills : {counts[ACTIVE]} active, "
    f"{counts[NEEDS_REVIEW]} needs_review, {counts[REJECTED]} rejected"
)
sys.exit(1 if counts[REJECTED] or result.catalog.errors else 0)