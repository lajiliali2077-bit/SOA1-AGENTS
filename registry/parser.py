"""Parser et validateur des fichiers SKILL.md (spécification Agent Skills, agentskills.io)."""

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import tiktoken
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

# name : minuscules, chiffres et tirets, sans tiret au début, à la fin ni doublé.
# Choix un peu plus strict que la spécification : ASCII uniquement.
NAME_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---[ \t]*(?:\n(.*))?\Z", re.DOTALL)
MAX_BODY_TOKENS = 5000  # recommandation de la spécification pour le corps


class SkillError(Exception):
    """Un fichier SKILL.md est invalide."""


class SkillMeta(BaseModel):
    """Frontmatter d'un SKILL.md : champs de la spécification, rien d'autre."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=1024)
    license: str | None = None
    compatibility: str | None = Field(default=None, min_length=1, max_length=500)
    metadata: dict[str, str] | None = None
    allowed_tools: list[str] = Field(default_factory=list, alias="allowed-tools")

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        if not NAME_PATTERN.fullmatch(value):
            raise ValueError(
                "doit contenir uniquement minuscules, chiffres et tirets, "
                "sans tiret au début, à la fin ni double"
            )
        return value

    @field_validator("allowed_tools", mode="before")
    @classmethod
    def split_tools(cls, value):
        # La spécification veut une chaîne séparée par des espaces, pas une liste YAML.
        if value is None:
            return []
        if isinstance(value, str):
            return value.split()
        raise ValueError("doit être une chaîne d'outils séparés par des espaces")


@dataclass
class ParsedSkill:
    meta: SkillMeta
    body: str
    path: Path
    department: str
    subdomain: str
    meta_tokens: int  # coût de l'entrée d'index (niveau 1)
    body_tokens: int  # coût du corps (niveau 2)
    warnings: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def _encoding():
    return tiktoken.get_encoding("o200k_base")


def count_tokens(text: str) -> int:
    """Estimation du nombre de tokens (tokenizer OpenAI, pas celui de Gemini)."""
    return len(_encoding().encode(text, disallowed_special=()))


def split_frontmatter(text: str) -> tuple[str, str]:
    """Sépare le frontmatter YAML du corps Markdown."""
    text = text.replace("\r\n", "\n").lstrip("\ufeff")
    match = FRONTMATTER.match(text)
    if not match:
        raise SkillError("frontmatter absent ou non fermé : le fichier doit commencer par '---'")
    return match.group(1), match.group(2) or ""


def parse_skill_file(path) -> ParsedSkill:
    """Lit, valide et mesure un SKILL.md. Lève SkillError si le fichier est invalide."""
    path = Path(path)
    try:
        return _parse(path)
    except SkillError as exc:
        raise SkillError(f"{path.as_posix()} : {exc}") from None


def _parse(path: Path) -> ParsedSkill:
    parts = path.resolve().parts
    if len(parts) < 6 or parts[-1] != "SKILL.md" or parts[-3] != "skills" or parts[-6] != "departments":
        raise SkillError("emplacement attendu : departments/<département>/<sous-domaine>/skills/<nom>/SKILL.md")
    department, subdomain = parts[-5], parts[-4]

    front, body = split_frontmatter(path.read_text(encoding="utf-8"))
    try:
        data = yaml.safe_load(front)
    except yaml.YAMLError as exc:
        raise SkillError(f"YAML invalide ({exc})") from exc
    if not isinstance(data, dict):
        raise SkillError("le frontmatter doit contenir des paires cle: valeur")

    try:
        meta = SkillMeta.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])} : {e['msg']}" for e in exc.errors()
        )
        raise SkillError(details) from None

    if meta.name != parts[-2]:
        raise SkillError(f"name '{meta.name}' différent du dossier '{parts[-2]}'")

    meta_tokens = count_tokens(f"{meta.name}: {meta.description}")
    body_tokens = count_tokens(body)

    warnings = []
    if "use when" not in meta.description.lower():
        warnings.append("la description ne contient pas 'Use when' (déclencheur manquant)")
    if body_tokens > MAX_BODY_TOKENS:
        warnings.append(f"corps de {body_tokens} tokens (recommandation : moins de {MAX_BODY_TOKENS})")

    return ParsedSkill(meta, body, path, department, subdomain, meta_tokens, body_tokens, warnings)


def discover_skills(departments_root) -> list[Path]:
    """Trouve tous les SKILL.md de departments/<dept>/<sous-domaine>/skills/<nom>/."""
    return sorted(Path(departments_root).glob("*/*/skills/*/SKILL.md"))