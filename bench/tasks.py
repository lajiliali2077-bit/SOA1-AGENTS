"""Tâches de test (tasks/finance/fin-01.yaml ...), lues et vérifiées avec Pydantic v2.

Une tâche = des messages de l'utilisateur (turns) + des vérifications (checks) sur les réponses.
"""

import re
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from django.conf import settings
from pydantic import BaseModel


class Check(BaseModel):
    check: Literal["skill_activated", "decision_is", "tool_called", "tool_not_called",
                   "text_contains", "text_matches", "iban_masked", "context_compacted"]
    turn: Optional[int] = None        # numéro du tour visé (sinon : tous / le dernier)
    skill: Optional[str] = None
    values: Optional[list] = None
    tool: Optional[str] = None
    arguments: Optional[dict] = None
    value: Any = None
    pattern: Optional[str] = None


class Turn(BaseModel):
    user: str

    @property
    def confirmed(self) -> bool:
        """L'utilisateur confirme explicitement une écriture (« je confirme »)."""
        return bool(re.search(r"je confirme|i confirm", self.user, re.IGNORECASE))


class Task(BaseModel):
    id: str
    department: str
    title: str
    expected_skill: str
    trap: str = "none"
    overridden_rule: str = "none"
    turns: list[Turn]
    tool_results: dict[str, str] = {}
    checks: list[Check]


def load_tasks() -> list:
    files = sorted((Path(settings.BASE_DIR) / "tasks").glob("*/*.yaml"))
    return [Task.model_validate(yaml.safe_load(f.read_text(encoding="utf-8"))) for f in files]


def get_task(task_id: str) -> Task:
    for task in load_tasks():
        if task.id == task_id:
            return task
    raise ValueError(f"tâche inconnue : '{task_id}'")
