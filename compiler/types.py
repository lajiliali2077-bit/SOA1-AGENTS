"""Types partagés du compilateur (voir docs/CONTRATS_INTERFACE.md, section 1)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    """Un élément de l'historique. On n'ajoute qu'à la fin, on ne modifie jamais."""

    kind: str           # "user" | "assistant" | "activate_skill" | "load_reference" | "observation"
    text: str = ""      # texte du message, ou sortie complète de l'outil
    skill: str = ""     # activate_skill, load_reference : nom du skill
    filename: str = ""  # load_reference : fichier du dossier references/ du skill
    tool: str = ""      # observation : nom de l'outil appelé
    obs_id: str = ""    # observation : identifiant donné par le Role 2 ("obs-0007")


@dataclass(frozen=True)
class ContextItem:
    """Un bloc du contexte compilé."""

    tier: int           # 1, 2, 3, ou 0 pour la conversation
    kind: str           # "agents" | "skill_index" | "skill_body" | "reference" | "user" | "assistant" | "observation" | "masked"
    text: str
    tokens: int
    source: str = ""    # chemin du fichier, nom du skill ou obs_id


@dataclass(frozen=True)
class CompileResult:
    """Résultat de compile_context."""

    text: str           # contexte complet, à envoyer à Gemini
    items: list         # liste de ContextItem (sert à mesurer la composition des tokens)
    tokens: int         # total estimé (blocs de texte + définitions des outils)
    budget: int
    prefix_tokens: int  # taille du Tier 1 (préfixe stable)
    active_skills: list # noms, du plus ancien au plus récent (2 maximum)
    allowed_tools: list # outils autorisés par les skills actifs
    tool_tokens: int    # somme de Tool.tokens des outils autorisés (déjà dans tokens)
    compacted: bool     # True si une éviction ou un masquage a eu lieu
    evictions: list     # ex. "masked:obs-0003", "unloaded:<fichier>", "deactivated:<skill>"