"""Lecture des fichiers du dépôt et enregistrement dans PostgreSQL.

    AGENTS.md                                   -> table AgentsFile
    departments/<dept>/<sous-domaine>/skills/<nom>/SKILL.md -> table Skill
    tools/<dept>.yaml                           -> table Tool

Règles de validation d'un skill :
- rejeté (pas enregistré) : en-tête invalide, outil inconnu, ou outil interdit au département ;
- needs_review : outil d'écriture, outil déclaré mais jamais cité, pas de « Use when »,
  ou corps de plus de 5000 tokens ;
- active : sinon.
"""

import json
from pathlib import Path
from typing import Literal, Optional

import tiktoken
import yaml
from django.conf import settings
from django.db import transaction
from pydantic import BaseModel, Field

from erp.tools import TOOLS

from .models import AgentsFile, Skill, Tool

ENCODING = tiktoken.get_encoding("o200k_base")
MAX_BODY_TOKENS = 5000


def count_tokens(text: str) -> int:
    """Nombre de tokens (tokenizer OpenAI : c'est une estimation pour Gemini)."""
    return len(ENCODING.encode(text, disallowed_special=()))


# ----- Formats vérifiés avec Pydantic v2 -----

class SkillHeader(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=64)
    description: str = Field(min_length=1, max_length=1024)
    allowed_tools: str = Field(default="", alias="allowed-tools")   # noms séparés par des espaces


class ToolParameter(BaseModel):
    name: str
    type: Literal["string", "number", "integer", "boolean"]
    required: bool = False
    enum: Optional[list[str]] = None
    description: str = ""


class ToolDefinition(BaseModel):
    name: str
    description: str
    mode: Literal["read", "write"]
    departments: list[str]
    parameters: list[ToolParameter] = []


# ----- Lecture des fichiers -----

def relative(path: Path) -> str:
    return Path(path).relative_to(settings.BASE_DIR).as_posix()


def read_tools() -> dict:
    """Tous les outils de tools/*.yaml : {nom: (ToolDefinition, département propriétaire)}."""
    tools = {}
    for path in sorted((settings.BASE_DIR / "tools").glob("*.yaml")):
        for item in yaml.safe_load(path.read_text(encoding="utf-8")):
            tool = ToolDefinition.model_validate(item)      # erreur si le format est faux
            if tool.name in tools:
                raise ValueError(f"outil '{tool.name}' défini deux fois")
            if tool.name not in TOOLS:
                raise ValueError(f"outil '{tool.name}' sans fonction Python dans erp/tools.py")
            tools[tool.name] = (tool, path.stem)
    return tools


def read_skill(path: Path) -> dict:
    """Lit un SKILL.md : en-tête YAML entre deux lignes ---, puis le corps en Markdown."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---" not in text[3:]:
        raise ValueError("en-tête YAML (---) manquant")
    header_text, body = text[4:].split("\n---", 1)
    header = SkillHeader.model_validate(yaml.safe_load(header_text))
    if header.name != path.parent.name:
        raise ValueError(f"name '{header.name}' différent du nom du dossier")
    body = body.lstrip("-").strip("\n")
    return {
        "name": header.name,
        "description": header.description,
        "allowed_tools": header.allowed_tools.split(),
        "department": path.parts[-5],
        "subdomain": path.parts[-4],
        "path": relative(path),
        "body": body,
        "index_tokens": count_tokens(f"{header.name}: {header.description}"),
        "body_tokens": count_tokens(body),
    }


def check_skill(skill: dict, tools: dict) -> tuple:
    """Retourne (statut, liste des problèmes)."""
    errors, warnings = [], []
    for name in skill["allowed_tools"]:
        if name not in tools:
            errors.append(f"outil inconnu : {name}")
            continue
        tool = tools[name][0]
        if skill["department"] not in tool.departments:
            errors.append(f"outil {name} interdit au département {skill['department']}")
        if tool.mode == "write":
            warnings.append(f"outil d'écriture {name} : validation humaine requise")
        if name not in skill["body"]:
            warnings.append(f"outil {name} déclaré mais jamais cité dans le corps")
    if "use when" not in skill["description"].lower():
        warnings.append("la description ne dit pas quand l'utiliser (« Use when »)")
    if skill["body_tokens"] > MAX_BODY_TOKENS:
        warnings.append(f"corps trop long ({skill['body_tokens']} tokens)")

    if errors:
        return "rejected", errors
    if warnings:
        return "needs_review", warnings
    return "active", []


def agents_files() -> list:
    """Tous les AGENTS.md avec leur niveau."""
    root = settings.BASE_DIR
    files = [(1, "", "", root / "AGENTS.md")]
    for path in sorted((root / "departments").glob("*/AGENTS.md")):
        files.append((2, path.parts[-2], "", path))
    for path in sorted((root / "departments").glob("*/*/AGENTS.md")):
        files.append((3, path.parts[-3], path.parts[-2], path))
    return files


# ----- Enregistrement en base -----

def index_all() -> dict:
    """Relit tout le dépôt et remplace le contenu des 3 tables. Retourne un résumé."""
    tools = read_tools()
    summary = {"active": [], "needs_review": {}, "rejected": {}}
    skills = []
    for path in sorted((settings.BASE_DIR / "departments").glob("*/*/skills/*/SKILL.md")):
        try:
            skill = read_skill(path)
        except Exception as exc:      # YAML ou en-tête invalide
            summary["rejected"][relative(path)] = [str(exc)]
            continue
        status, problems = check_skill(skill, tools)
        if status == "rejected":
            summary["rejected"][skill["path"]] = problems
            continue
        if status == "needs_review":
            summary["needs_review"][skill["path"]] = problems
        else:
            summary["active"].append(skill["path"])
        skills.append(Skill(status=status, **skill))

    with transaction.atomic():      # tout ou rien
        Tool.objects.all().delete()
        Skill.objects.all().delete()
        AgentsFile.objects.all().delete()
        for name, (tool, owner) in tools.items():
            data = tool.model_dump(exclude_defaults=True)
            Tool.objects.create(
                name=name, description=tool.description, mode=tool.mode, owner=owner,
                departments=tool.departments,
                parameters=[p.model_dump(exclude_none=True) for p in tool.parameters],
                tokens=count_tokens(json.dumps(data, ensure_ascii=False)))
        Skill.objects.bulk_create(skills)
        for level, department, subdomain, path in agents_files():
            content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
            AgentsFile.objects.create(path=relative(path), level=level, department=department,
                                      subdomain=subdomain, content=content,
                                      tokens=count_tokens(content))

    summary["counts"] = {"tools": Tool.objects.count(), "skills": Skill.objects.count(),
                         "agents": AgentsFile.objects.count()}
    return summary


def department_tokens(department: str) -> dict:
    """Taille d'un département : tous ses fichiers .md + ses outils (critère de l'énoncé)."""
    folder = settings.BASE_DIR / "departments" / department
    markdown = sum(count_tokens(p.read_text(encoding="utf-8")) for p in folder.rglob("*.md"))
    tools = sum(Tool.objects.filter(owner=department).values_list("tokens", flat=True))
    return {"markdown": markdown, "tools": tools, "total": markdown + tools}
