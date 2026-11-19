"""Conversion JSON <-> types du compilateur (pour les vues JSON du Role 5).

Une entrée invalide lève ValueError : la vue peut répondre par une erreur 400 claire.
"""

from dataclasses import asdict, fields

from .types import CompileResult, Event

EVENT_FIELDS = {f.name for f in fields(Event)}


def event_from_dict(data) -> Event:
    """Construit un Event à partir d'un dictionnaire JSON, en vérifiant les champs."""
    if not isinstance(data, dict):
        raise ValueError("un événement doit être un objet JSON")
    unknown = set(data) - EVENT_FIELDS
    if unknown:
        raise ValueError(f"champs inconnus dans l'événement : {sorted(unknown)}")
    if not data.get("kind"):
        raise ValueError("champ 'kind' manquant dans l'événement")
    for name, value in data.items():
        if not isinstance(value, str):
            raise ValueError(f"le champ '{name}' doit être du texte")
    return Event(**data)


def events_from_list(data) -> list:
    """Construit la liste d'événements à partir d'une liste JSON."""
    if not isinstance(data, list):
        raise ValueError("'events' doit être une liste")
    return [event_from_dict(item) for item in data]


def result_to_dict(result: CompileResult) -> dict:
    """Transforme un CompileResult en dictionnaire prêt pour json.dumps."""
    return asdict(result)