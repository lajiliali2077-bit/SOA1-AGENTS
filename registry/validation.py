"""Validation des skills contre le catalogue d'outils : gravité (erreur, avertissement, info) et statut.

Statut d'un skill : rejected s'il a une erreur, needs_review s'il a un avertissement,
active sinon. Ces règles sont propres au projet, la spécification SKILL.md ne les impose pas.
Aucun département n'est en lecture seule : tout département peut avoir des outils d'écriture,
qui donnent un avertissement (validation humaine requise).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from .parser import ParsedSkill, SkillError, discover_skills, parse_skill_file
from .tools import Catalog, known_departments, load_catalog

ERROR, WARNING, INFO = "error", "warning", "info"
ACTIVE, NEEDS_REVIEW, REJECTED = "active", "needs_review", "rejected"

# Chemin relatif cité dans un corps, par exemple references/invoice_schema.md
REFERENCE_PATTERN = re.compile(r"references/[\w-]+(?:\.[\w-]+)*")


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    message: str


@dataclass
class SkillReport:
    path: Path
    name: str
    department: str
    subdomain: str
    issues: list[Issue] = field(default_factory=list)
    skill: ParsedSkill | None = None  # None si le parsing a échoué

    @property
    def status(self) -> str:
        if any(i.severity == ERROR for i in self.issues):
            return REJECTED
        if any(i.severity == WARNING for i in self.issues):
            return NEEDS_REVIEW
        return ACTIVE


@dataclass
class ValidationResult:
    reports: list[SkillReport]
    catalog: Catalog


def mentions(text: str, tool_name: str) -> bool:
    """Le nom d'outil apparaît-il tel quel dans le texte (pas comme partie d'un autre nom) ?"""
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(tool_name)}(?![A-Za-z0-9_])"
    return re.search(pattern, text) is not None


def check_skill(skill: ParsedSkill, catalog: Catalog) -> list[Issue]:
    issues = []
    department = skill.department
    declared = skill.meta.allowed_tools

    # Outils déclarés : existence, périmètre, mode
    for tool_name in declared:
        tool = catalog.tools.get(tool_name)
        if tool is None:
            issues.append(Issue(ERROR, "E_TOOL_UNKNOWN", f"outil '{tool_name}' absent du catalogue"))
            continue
        if department not in tool.departments:
            issues.append(Issue(
                ERROR, "E_TOOL_FORBIDDEN",
                f"outil '{tool_name}' non autorisé pour '{department}' "
                f"(départements autorisés : {', '.join(tool.departments)})",
            ))
            continue
        if tool.mode == "write":
            issues.append(Issue(
                WARNING, "W_WRITE_TOOL",
                f"outil d'écriture '{tool_name}' : validation humaine requise",
            ))

    # Cohérence entre allowed-tools et le corps du skill
    for tool_name in catalog.tools:
        if tool_name not in declared and mentions(skill.body, tool_name):
            issues.append(Issue(
                WARNING, "W_TOOL_UNDECLARED",
                f"le corps cite '{tool_name}' qui n'est pas dans allowed-tools",
            ))
    for tool_name in declared:
        if not mentions(skill.body, tool_name):
            issues.append(Issue(
                WARNING, "W_TOOL_UNUSED",
                f"'{tool_name}' est déclaré mais jamais cité dans le corps (privilège inutile)",
            ))

    # Fichiers de niveau 3 (references/)
    skill_dir = skill.path.parent
    cited = set(REFERENCE_PATTERN.findall(skill.body))
    for ref in sorted(cited):
        if not (skill_dir / ref).is_file():
            issues.append(Issue(WARNING, "W_REFERENCE_MISSING", f"fichier cité introuvable : {ref}"))
    refs_dir = skill_dir / "references"
    if refs_dir.is_dir():
        for file in sorted(refs_dir.rglob("*")):
            if file.is_file():
                relative = file.relative_to(skill_dir).as_posix()
                if relative not in cited:
                    issues.append(Issue(INFO, "I_REFERENCE_UNUSED", f"{relative} n'est cité nulle part dans le SKILL.md"))

    # Avertissements du parser (par exemple description sans "Use when")
    for text in skill.warnings:
        issues.append(Issue(WARNING, "W_PARSER", text))

    issues.append(Issue(
        INFO, "I_TOKENS",
        f"index {skill.meta_tokens} tokens, corps {skill.body_tokens} tokens, {len(declared)} outil(s) déclaré(s)",
    ))
    return issues


def validate_all(departments_root, tools_dir) -> ValidationResult:
    """Charge le catalogue, parse et valide chaque skill, détecte les noms en double."""
    departments_root = Path(departments_root)
    catalog = load_catalog(tools_dir, known_departments(departments_root))

    reports = []
    for path in discover_skills(departments_root):
        department, subdomain, folder = path.parts[-5], path.parts[-4], path.parts[-2]
        try:
            skill = parse_skill_file(path)
        except SkillError as exc:
            message = str(exc).split(" : ", 1)[-1]  # retire le chemin, déjà connu
            reports.append(SkillReport(path, folder, department, subdomain, [Issue(ERROR, "E_PARSE", message)]))
            continue
        reports.append(SkillReport(path, skill.meta.name, department, subdomain, check_skill(skill, catalog), skill))

    by_name: dict[str, list[SkillReport]] = {}
    for report in reports:
        by_name.setdefault(report.name, []).append(report)
    for name, group in by_name.items():
        if len(group) > 1:
            for report in group:
                report.issues.append(Issue(ERROR, "E_DUPLICATE_NAME", f"nom '{name}' utilisé par {len(group)} skills"))

    return ValidationResult(reports, catalog)