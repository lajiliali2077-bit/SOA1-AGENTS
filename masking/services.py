"""Service de masquage des sorties d'outils.

Une sortie d'outil peut faire des milliers de lignes. On la garde en entier dans la base
(table Observation), et dans le contexte on peut la remplacer par une ligne courte :
    [sortie masquée : get_invoice, 350 lignes, 20000 tokens, id obs-0007]
La sortie complète reste disponible avec recall_observation("obs-0007").
"""

from dataclasses import replace

from .models import Observation

THRESHOLD = 0.7   # on masque dès que le contexte atteint 70 % du budget
KEEP_LAST = 2     # les 2 dernières sorties restent en clair


def record_observation(tool: str, output: str) -> str:
    """Enregistre la sortie complète d'un outil et retourne son identifiant (ex. obs-0007)."""
    return Observation.objects.create(tool=tool, output=output).obs_id


def recall_observation(obs_id: str) -> str:
    """Retourne la sortie complète d'une observation."""
    try:
        number = int(obs_id.replace("obs-", ""))
        return Observation.objects.get(pk=number).output
    except (ValueError, Observation.DoesNotExist):
        raise ValueError(f"observation inconnue : {obs_id}") from None


def mask_observations(blocks: list, budget: int, extra_tokens: int = 0) -> tuple:
    """Remplace les anciennes observations par une ligne courte si le contexte est trop gros.

    blocks : blocs du contexte (compiler.core.Block) ; extra_tokens : tokens des outils.
    Retourne (nouveaux blocs, identifiants masqués).
    """
    total = sum(b.tokens for b in blocks) + extra_tokens
    if total < THRESHOLD * budget:
        return blocks, []

    observations = [b for b in blocks if b.kind == "observation"]
    to_mask = observations[:-KEEP_LAST]
    new_blocks, masked = [], []
    for block in blocks:
        if block in to_mask:
            tool = block.text.split("(", 1)[1].split(",", 1)[0]   # "Observation (outil, id) :"
            lines = len(block.text.splitlines()) - 1
            text = f"[sortie masquée : {tool}, {lines} lignes, {block.tokens} tokens, id {block.source}]"
            block = replace(block, kind="masked", text=text, tokens=0)   # tokens recalculés
            masked.append(block.source)
        new_blocks.append(block)
    return new_blocks, masked
