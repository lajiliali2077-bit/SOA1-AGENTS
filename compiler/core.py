"""Compilateur de contexte progressif (version 2 : Tier 1, activation de skill, conversation).

Principe : compile_context est une fonction PURE. Mêmes événements = même contexte.
Elle lit seulement la base du registre. Le texte est construit en ajoutant des blocs
à la fin, séparés par une ligne vide, donc le texte de n événements est toujours le
début du texte de n+1 événements (préfixe stable, compatible avec le cache KV).
"""

from registry.models import AgentsFile, Skill, Tool
from registry.parser import count_tokens

from .types import CompileResult, ContextItem, Event

SEPARATOR = "\n\n"
CONVERSATION_PREFIXES = {"user": "Utilisateur : ", "assistant": "Assistant : "}
NOT_IMPLEMENTED_KINDS = {"load_reference", "observation"}
MAX_ACTIVE_SKILLS = 2


def _tier1_items() -> list:
    """Tier 1 : AGENTS.md global, puis index des skills. Toujours présent, jamais évincé."""
    items = []
    root = AgentsFile.objects.filter(level=AgentsFile.Level.GLOBAL).first()
    if root is not None:
        items.append(ContextItem(tier=1, kind="agents", text=root.content,
                                 tokens=root.tokens, source=root.path))
    # L'ordre vient de Skill.Meta.ordering (département, sous-domaine, nom) : il est stable.
    lines = [f"- {s.name} ({s.department}) : {s.description}" for s in Skill.objects.all()]
    index_text = "Skills disponibles :\n" + "\n".join(lines)
    items.append(ContextItem(tier=1, kind="skill_index", text=index_text,
                             tokens=count_tokens(index_text), source="skill_index"))
    return items


def _conversation_item(event: Event) -> ContextItem:
    """Transforme un événement user ou assistant en bloc de conversation (tier 0)."""
    text = CONVERSATION_PREFIXES[event.kind] + event.text
    return ContextItem(tier=0, kind=event.kind, text=text, tokens=count_tokens(text))


def _find_skill(name: str) -> Skill:
    """Cherche un skill par son nom. Erreur s'il n'existe pas ou si le nom est ambigu."""
    matches = list(Skill.objects.filter(name=name))
    if not matches:
        raise ValueError(f"skill inconnu : '{name}'")
    if len(matches) > 1:
        raise ValueError(f"nom de skill ambigu : '{name}' existe dans plusieurs départements")
    return matches[0]


def _activation_items(skill_name: str, active: list, added_sources: set) -> list:
    """Blocs ajoutés par l'activation d'un skill (Tier 2), dans cet ordre :
    AGENTS.md du département, AGENTS.md du sous-domaine, corps du skill.
    Le plus spécifique est le plus proche de la fin : il a priorité (règle surchargée).
    `active` et `added_sources` sont mis à jour ici.
    """
    skill = _find_skill(skill_name)
    if any(s.pk == skill.pk for s in active):
        return []  # déjà actif : on n'ajoute rien, le contexte reste append-only
    if len(active) >= MAX_ACTIVE_SKILLS:
        raise NotImplementedError(
            "3e skill actif : la désactivation du plus ancien sera faite avec l'éviction")
    active.append(skill)

    candidates = [
        AgentsFile.objects.filter(level=AgentsFile.Level.DEPARTMENT,
                                  department=skill.department).first(),
        AgentsFile.objects.filter(level=AgentsFile.Level.SUBDOMAIN,
                                  department=skill.department,
                                  subdomain=skill.subdomain).first(),
    ]
    items = []
    for agents in candidates:
        # Absent de la base, ou déjà ajouté par un autre skill : on saute.
        if agents is None or agents.path in added_sources:
            continue
        added_sources.add(agents.path)
        items.append(ContextItem(tier=2, kind="agents", text=agents.content,
                                 tokens=agents.tokens, source=agents.path))

    body_text = f"Skill activé : {skill.name}\n\n{skill.body}"
    items.append(ContextItem(tier=2, kind="skill_body", text=body_text,
                             tokens=count_tokens(body_text), source=skill.name))
    return items


def _allowed_tools(active: list) -> list:
    """Outils autorisés par les skills actifs, sans doublon, dans l'ordre des skills."""
    names = []
    for skill in active:
        for tool in skill.allowed_tools:
            if tool not in names:
                names.append(tool)
    return names


def compile_context(events: list, budget: int = 6000, mode: str = "progressive") -> CompileResult:
    """Assemble le contexte pour la liste d'événements donnée (voir le contrat, section 2)."""
    if mode != "progressive":
        raise NotImplementedError(f"mode '{mode}' pas encore implémenté")

    items = _tier1_items()
    prefix_tokens = sum(item.tokens for item in items)

    active = []          # skills actifs, du plus ancien au plus récent
    added_sources = set()  # chemins des AGENTS.md déjà ajoutés (évite les doublons)

    for event in events:
        if event.kind in CONVERSATION_PREFIXES:
            items.append(_conversation_item(event))
        elif event.kind == "activate_skill":
            items.extend(_activation_items(event.skill, active, added_sources))
        elif event.kind in NOT_IMPLEMENTED_KINDS:
            raise NotImplementedError(f"événement '{event.kind}' pas encore implémenté")
        else:
            raise ValueError(f"type d'événement inconnu : '{event.kind}'")

    allowed_tools = _allowed_tools(active)
    tool_tokens = sum(Tool.objects.filter(name__in=allowed_tools).values_list("tokens", flat=True))

    return CompileResult(
        text=SEPARATOR.join(item.text for item in items),
        items=items,
        tokens=sum(item.tokens for item in items) + tool_tokens,
        budget=budget,
        prefix_tokens=prefix_tokens,
        active_skills=[s.name for s in active],
        allowed_tools=allowed_tools,
        tool_tokens=tool_tokens,
        compacted=False,   # pas encore d'éviction dans cette version
        evictions=[],
    )