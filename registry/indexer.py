"""Indexation du registre : valide departments/ et tools/, puis enregistre en base.

Règles :
- catalogue d'outils invalide : rien n'est écrit (les permissions en dépendent) ;
- skill rejeté : exclu du registre (et supprimé s'il y était), les autres skills sont indexés ;
- skill active ou needs_review : indexé avec son statut et ses problèmes ;
- une seule transaction, relançable (clé : chemin relatif du fichier).
"""

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import AgentsFile, Skill, Tool
from .parser import count_tokens
from .validation import NEEDS_REVIEW, REJECTED, SkillReport, validate_all


@dataclass
class IndexReport:
    catalog_errors: list[str] = field(default_factory=list)
    rejected: list[SkillReport] = field(default_factory=list)
    needs_review: list[SkillReport] = field(default_factory=list)
    status_counts: Counter = field(default_factory=Counter)
    created: Counter = field(default_factory=Counter)    # clés : tools, skills, agents
    refreshed: Counter = field(default_factory=Counter)
    removed: Counter = field(default_factory=Counter)
    written: bool = False


def relative_path(path) -> str:
    """Chemin relatif à la racine du dépôt, avec des / (identique sur toutes les machines)."""
    return Path(path).resolve().relative_to(settings.BASE_DIR).as_posix()


def discover_agents_files(base_dir: Path, departments_root: Path) -> list[tuple]:
    """Retourne (niveau, département, sous-domaine, chemin) pour chaque AGENTS.md."""
    items = []
    root_file = base_dir / "AGENTS.md"
    if root_file.is_file():
        items.append((1, "", "", root_file))
    for path in sorted(departments_root.glob("*/AGENTS.md")):
        items.append((2, path.parts[-2], "", path))
    for path in sorted(departments_root.glob("*/*/AGENTS.md")):
        items.append((3, path.parts[-3], path.parts[-2], path))
    return items


def _sync(report: IndexReport, label: str, model, key_field: str, rows: list[tuple]) -> None:
    """Crée ou met à jour chaque ligne (clé, valeurs) et supprime celles qui ne figurent plus dans rows."""
    keys = [key for key, _ in rows]
    stale = model.objects.exclude(**{f"{key_field}__in": keys})
    report.removed[label] += stale.count()
    stale.delete()
    for key, defaults in rows:
        _, created = model.objects.update_or_create(**{key_field: key}, defaults=defaults)
        (report.created if created else report.refreshed)[label] += 1


def index_all() -> IndexReport:
    report = IndexReport()
    base_dir = Path(settings.BASE_DIR)
    departments_root = base_dir / "departments"
    result = validate_all(departments_root, base_dir / "tools")

    if result.catalog.errors:
        report.catalog_errors = list(result.catalog.errors)
        return report  # rien n'est écrit

    skill_rows = []
    for r in result.reports:
        report.status_counts[r.status] += 1
        if r.status == REJECTED:
            report.rejected.append(r)
            continue
        if r.status == NEEDS_REVIEW:
            report.needs_review.append(r)
        s = r.skill
        skill_rows.append((relative_path(r.path), {
            "name": s.meta.name,
            "description": s.meta.description,
            "allowed_tools": s.meta.allowed_tools,
            "department": s.department,
            "subdomain": s.subdomain,
            "body": s.body,
            "meta_tokens": s.meta_tokens,
            "body_tokens": s.body_tokens,
            "status": r.status,
            "issues": [{"severity": i.severity, "code": i.code, "message": i.message} for i in r.issues],
        }))

    tool_rows = []
    for name, tool in result.catalog.tools.items():
        data = tool.model_dump(exclude_unset=True)  # mêmes clés que le YAML, comme measure_corpus.py
        tool_rows.append((name, {
            "description": tool.description,
            "mode": tool.mode,
            "owner": result.catalog.owners[name],
            "departments": list(tool.departments),
            "parameters": [p.model_dump(exclude_unset=True) for p in tool.parameters],
            "tokens": count_tokens(json.dumps(data, ensure_ascii=False)),
        }))

    agents_rows = []
    for level, department, subdomain, path in discover_agents_files(base_dir, departments_root):
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        agents_rows.append((relative_path(path), {
            "level": level,
            "department": department,
            "subdomain": subdomain,
            "content": text,
            "tokens": count_tokens(text),
        }))

    with transaction.atomic():
        _sync(report, "tools", Tool, "name", tool_rows)
        _sync(report, "skills", Skill, "path", skill_rows)
        _sync(report, "agents", AgentsFile, "path", agents_rows)
    report.written = True
    return report