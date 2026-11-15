"""Catalogue d'outils : définitions complètes (description, paramètres, mode) par département.

La spécification SKILL.md ne connaît que des noms d'outils (allowed-tools). Le catalogue
est propre à notre harnais : il fixe le mode (lecture ou écriture) de chaque outil et les
départements autorisés à l'utiliser. Il sert de source aux permissions.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

TOOL_NAME = re.compile(r"[a-z][a-z0-9_]*")


class ToolParam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    type: Literal["string", "number", "integer", "boolean"]
    required: bool = False
    enum: list[str] | None = None
    description: str = Field(min_length=1)


class ToolDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = Field(min_length=1)
    mode: Literal["read", "write"]
    departments: list[str] = Field(min_length=1)
    parameters: list[ToolParam] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        if not TOOL_NAME.fullmatch(value):
            raise ValueError("doit être en minuscules avec des underscores, par exemple get_vendor")
        return value

    @field_validator("parameters")
    @classmethod
    def check_unique_parameters(cls, value):
        names = [p.name for p in value]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"paramètres en double : {', '.join(duplicates)}")
        return value


@dataclass
class Catalog:
    tools: dict[str, ToolDef] = field(default_factory=dict)
    owners: dict[str, str] = field(default_factory=dict)  # outil -> département propriétaire
    errors: list[str] = field(default_factory=list)


def known_departments(departments_root) -> set[str]:
    """Les départements sont les dossiers de departments/."""
    return {p.name for p in Path(departments_root).iterdir() if p.is_dir()}


def load_catalog(tools_dir, departments: set[str]) -> Catalog:
    """Charge tools/<département>.yaml. Les erreurs sont collectées, pas levées."""
    catalog = Catalog()
    for path in sorted(Path(tools_dir).glob("*.yaml")):
        owner = path.stem
        label = f"tools/{path.name}"
        if owner not in departments:
            catalog.errors.append(f"{label} : le nom du fichier ne correspond à aucun département")
        try:
            items = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            catalog.errors.append(f"{label} : YAML invalide ({exc})")
            continue
        if not isinstance(items, list):
            catalog.errors.append(f"{label} : le fichier doit contenir une liste d'outils")
            continue

        for index, item in enumerate(items, start=1):
            try:
                tool = ToolDef.model_validate(item)
            except ValidationError as exc:
                details = "; ".join(
                    f"{'.'.join(str(p) for p in e['loc'])} : {e['msg']}" for e in exc.errors()
                )
                catalog.errors.append(f"{label} (outil n°{index}) : {details}")
                continue
            if tool.name in catalog.tools:
                catalog.errors.append(
                    f"{label} : outil '{tool.name}' déjà défini dans tools/{catalog.owners[tool.name]}.yaml"
                )
                continue
            if owner not in tool.departments:
                catalog.errors.append(
                    f"{label} : '{tool.name}' doit inclure '{owner}' dans departments (le propriétaire)"
                )
            unknown = [d for d in tool.departments if d not in departments]
            if unknown:
                catalog.errors.append(
                    f"{label} : '{tool.name}' cite des départements inconnus : {', '.join(unknown)}"
                )
            catalog.tools[tool.name] = tool
            catalog.owners[tool.name] = owner
    return catalog