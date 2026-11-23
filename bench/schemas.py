"""Format des réponses de l'IA, vérifié avec Pydantic v2.

L'IA répond toujours par UN objet JSON qui contient une action :
    {"action": "activate_skill", "skill": "invoice-validation"}
    {"action": "load_reference", "skill": "invoice-validation", "filename": "approval_matrix.md"}
    {"action": "call_tool", "tool": "get_invoice", "arguments_json": "{\"invoice_id\": \"INV-1\"}"}
    {"action": "answer", "text": "Decision: HOLD ..."}

On ne fait jamais confiance à l'IA : si le JSON ne respecte pas ce format, rien n'est exécuté.
(Les arguments sont dans une chaîne JSON car le schéma imposé à Gemini doit rester simple.)
"""

import json
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, ValidationError


class AgentStep(BaseModel):
    model_config = ConfigDict(extra="forbid")   # champ inconnu = refusé

    action: Literal["activate_skill", "load_reference", "call_tool", "answer"]
    skill: Optional[str] = None
    filename: Optional[str] = None
    tool: Optional[str] = None
    arguments_json: Optional[str] = None
    text: Optional[str] = None

    @property
    def arguments(self) -> dict:
        return json.loads(self.arguments_json) if self.arguments_json else {}


# Champ obligatoire pour chaque action
REQUIRED = {
    "activate_skill": ["skill"],
    "load_reference": ["skill", "filename"],
    "call_tool": ["tool"],
    "answer": ["text"],
}


class StepError(ValueError):
    """Réponse de l'IA refusée par le moteur."""


def parse_step(raw: str) -> AgentStep:
    """Transforme le texte de l'IA en AgentStep, ou lève StepError."""
    try:
        step = AgentStep.model_validate_json(raw or "")
    except ValidationError as exc:
        raise StepError(f"format invalide : {exc.errors()[0]['msg']}") from None

    for name in REQUIRED[step.action]:
        if not getattr(step, name):
            raise StepError(f"champ '{name}' obligatoire pour l'action {step.action}")
    if step.filename and ("/" in step.filename or "\\" in step.filename or ".." in step.filename):
        raise StepError("filename doit être un simple nom de fichier")
    if step.arguments_json:
        try:
            if not isinstance(step.arguments, dict):
                raise ValueError
        except ValueError:
            raise StepError("arguments_json doit contenir un objet JSON") from None
    return step


# Le même format, donné à Gemini pour qu'il réponde directement en JSON valide.
GEMINI_SCHEMA = AgentStep.model_json_schema()
