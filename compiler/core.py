"""Compilateur de contexte (version 5 : modes progressif et monolithique, avec éviction).

Principe : compile_context est une fonction PURE. Mêmes événements = même contexte.
Elle lit la base du registre et, pour load_reference, un fichier du dépôt.
Le texte est construit en ajoutant des blocs à la fin, séparés par une ligne vide,
donc, tant qu'aucune éviction n'a eu lieu, le texte de n événements est toujours le début
du texte de n+1 événements (préfixe stable, compatible avec le cache KV).

Deux modes :
- "progressive" : Tier 1 au départ, puis Tier 2 et Tier 3 seulement au besoin,
                  avec éviction quand le budget est dépassé.
- "monolithic"  : tout est chargé au départ, sans éviction (sert de comparaison au benchmark).

Éviction (mode progressif seulement). Le masquage des observations (Role 2) n'existe pas
encore : il se branchera dans _enforce_budget, AVANT l'étape 1.
- Un 3e skill actif désactive toujours le plus ancien (règle fixe, sans lien avec le budget).
- Quand le total dépasse le budget, après chaque événement :
    étape 1 : on décharge les références (Tier 3), la plus ancienne d'abord ;
    étape 2 : on désactive le skill actif le plus ancien (jamais le plus récent).
- Jamais évincés : Tier 1 (AGENTS.md global + index) et la conversation.
- Si c'est encore trop gros après ça, le budget reste dépassé (on ne ment pas sur la taille).
"""

from pathlib import Path

from registry.models import AgentsFile, Skill, Tool
from registry.parser import count_tokens

from .types import CompileResult, ContextItem, Event

SEPARATOR = "\n\n"
CONVERSATION_PREFIXES = {"user": "Utilisateur : ", "assistant": "Assistant : "}
NOT_IMPLEMENTED_KINDS = {"observation"}
MAX_ACTIVE_SKILLS = 2
MODES = ("progressive", "monolithic")

# Racine du dépôt : compiler/core.py est un niveau sous la racine (là où se trouve manage.py).
# Les tests remplacent cette valeur par un dossier temporaire.
REPO_ROOT = Path(__file__).resolve().parent.parent


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


def _monolithic_items() -> tuple:
    """Mode monolithique : tous les AGENTS.md, puis tous les corps de skills.
    Les tiers sont les mêmes qu'en mode progressif (global = 1, le reste = 2) pour que
    la composition des tokens soit comparable. Retourne (items, liste de tous les skills).
    """
    items = []
    # L'ordre vient de AgentsFile.Meta.ordering (niveau, département, sous-domaine).
    for agents in AgentsFile.objects.all():
        tier = 1 if agents.level == AgentsFile.Level.GLOBAL else 2
        items.append(ContextItem(tier=tier, kind="agents", text=agents.content,
                                 tokens=agents.tokens, source=agents.path))
    skills = list(Skill.objects.all())
    for skill in skills:
        text = f"Skill : {skill.name}\n\n{skill.body}"
        items.append(ContextItem(tier=2, kind="skill_body", text=text,
                                 tokens=count_tokens(text), source=skill.name))
    return items, skills


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


def _agents_candidates(skill: Skill) -> list:
    """Les AGENTS.md qui concernent un skill et qui existent en base :
    celui du département, puis celui du sous-domaine."""
    candidates = [
        AgentsFile.objects.filter(level=AgentsFile.Level.DEPARTMENT,
                                  department=skill.department).first(),
        AgentsFile.objects.filter(level=AgentsFile.Level.SUBDOMAIN,
                                  department=skill.department,
                                  subdomain=skill.subdomain).first(),
    ]
    return [agents for agents in candidates if agents is not None]


def _deactivate_skill(skill: Skill, items: list, active: list,
                      added_sources: set, loaded: set) -> None:
    """Désactive un skill : retire son corps, ses références, et ses AGENTS.md
    que plus aucun skill actif n'utilise. `items`, `active`, `added_sources` et `loaded`
    sont modifiés sur place.
    """
    active[:] = [s for s in active if s.pk != skill.pk]
    refs_prefix = Path(skill.path).parent.as_posix() + "/references/"
    # AGENTS.md encore utiles aux skills restants : on ne les retire pas.
    still_needed = {a.path for other in active for a in _agents_candidates(other)}
    agents_to_drop = {a.path for a in _agents_candidates(skill)} - still_needed

    kept = []
    for item in items:
        is_body = item.kind == "skill_body" and item.source == skill.name
        is_reference = item.kind == "reference" and item.source.startswith(refs_prefix)
        is_agents = item.kind == "agents" and item.source in agents_to_drop
        if is_reference:
            loaded.discard(item.source)       # la référence pourra être rechargée plus tard
        if is_agents:
            added_sources.discard(item.source)  # l'AGENTS.md pourra être rajouté plus tard
        if not (is_body or is_reference or is_agents):
            kept.append(item)
    items[:] = kept


def _activate_skill(skill_name: str, items: list, active: list, added_sources: set,
                    loaded: set, evictions: list) -> None:
    """Active un skill et ajoute à la fin (Tier 2), dans cet ordre :
    AGENTS.md du département, AGENTS.md du sous-domaine, corps du skill.
    Le plus spécifique est le plus proche de la fin : il a priorité (règle surchargée).
    S'il y a déjà 2 skills actifs, le plus ancien est désactivé d'abord.
    """
    skill = _find_skill(skill_name)
    if any(s.pk == skill.pk for s in active):
        return  # déjà actif : on n'ajoute rien, le contexte reste append-only

    while len(active) >= MAX_ACTIVE_SKILLS:
        oldest = active[0]
        _deactivate_skill(oldest, items, active, added_sources, loaded)
        evictions.append(f"deactivated:{oldest.name}")
    active.append(skill)

    for agents in _agents_candidates(skill):
        # Déjà ajouté (par un autre skill encore actif) : on saute.
        if agents.path in added_sources:
            continue
        added_sources.add(agents.path)
        items.append(ContextItem(tier=2, kind="agents", text=agents.content,
                                 tokens=agents.tokens, source=agents.path))

    body_text = f"Skill activé : {skill.name}\n\n{skill.body}"
    items.append(ContextItem(tier=2, kind="skill_body", text=body_text,
                             tokens=count_tokens(body_text), source=skill.name))


def _reference_items(skill_name: str, filename: str, active: list, loaded: set) -> list:
    """Bloc ajouté par load_reference (Tier 3) : un fichier du dossier references/ d'un skill.
    `loaded` mémorise les chemins déjà chargés (pas de doublon).
    """
    skill = next((s for s in active if s.name == skill_name), None)
    if skill is None:
        raise ValueError(f"skill '{skill_name}' non actif : activez-le avant de charger ses références")

    # Sécurité : seulement un nom de fichier simple, jamais un chemin.
    if filename in ("", ".", "..") or "/" in filename or "\\" in filename:
        raise ValueError(f"nom de fichier de référence invalide : '{filename}'")

    relative = Path(skill.path).parent / "references" / filename
    key = relative.as_posix()
    if key in loaded:
        return []  # déjà chargé : on n'ajoute rien

    folder = (REPO_ROOT / Path(skill.path).parent / "references").resolve()
    file_path = (REPO_ROOT / relative).resolve()
    # Deuxième barrière : le fichier doit vraiment se trouver dans references/ du skill.
    if folder not in file_path.parents or not file_path.is_file():
        raise ValueError(f"référence introuvable : {skill.name}/{filename}")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"référence illisible (pas du texte UTF-8) : {skill.name}/{filename}") from None
    content = content.replace("\r\n", "\n")  # même texte sur toutes les machines

    loaded.add(key)
    text = f"Référence : {skill.name}/{filename}\n\n{content}"
    return [ContextItem(tier=3, kind="reference", text=text, tokens=count_tokens(text),
                        source=key)]


def _allowed_tools(active: list) -> list:
    """Outils autorisés par les skills actifs, sans doublon, dans l'ordre des skills."""
    names = []
    for skill in active:
        for tool in skill.allowed_tools:
            if tool not in names:
                names.append(tool)
    return names


def _tool_tokens(tool_names: list) -> int:
    """Somme des tokens des définitions des outils donnés."""
    return sum(Tool.objects.filter(name__in=tool_names).values_list("tokens", flat=True))


def _total_tokens(items: list, active: list) -> int:
    """Taille actuelle du contexte : blocs de texte + définitions des outils autorisés."""
    return sum(item.tokens for item in items) + _tool_tokens(_allowed_tools(active))


def _enforce_budget(items: list, active: list, added_sources: set, loaded: set,
                    evictions: list, budget: int, keep_source: str = "") -> None:
    """Ramène le contexte dans le budget si possible (mode progressif seulement).

    keep_source : bloc ajouté par l'événement en cours (une référence que l'IA vient de
    demander). Il est protégé pendant cet événement : sinon il serait déchargé aussitôt.
    Il redevient évinçable à l'événement suivant. Pendant ce temps, on ne désactive aucun
    skill (la référence protégée pourrait appartenir au skill le plus ancien).
    """
    # (Le masquage des observations du Role 2 viendra ici, avant l'étape 1.)

    # Étape 1 : décharger les références, la plus ancienne d'abord.
    while _total_tokens(items, active) > budget:
        index = next((i for i, item in enumerate(items)
                      if item.kind == "reference" and item.source != keep_source), None)
        if index is None:
            break
        removed = items.pop(index)
        loaded.discard(removed.source)
        evictions.append(f"unloaded:{removed.source}")

    # Étape 2 : désactiver le skill le plus ancien. On garde toujours au moins un skill.
    while not keep_source and len(active) > 1 and _total_tokens(items, active) > budget:
        oldest = active[0]
        _deactivate_skill(oldest, items, active, added_sources, loaded)
        evictions.append(f"deactivated:{oldest.name}")


def compile_context(events: list, budget: int = 6000, mode: str = "progressive") -> CompileResult:
    """Assemble le contexte pour la liste d'événements donnée (voir le contrat, section 2)."""
    if mode not in MODES:
        raise ValueError(f"mode inconnu : '{mode}' (attendu : {', '.join(MODES)})")
    monolithic = mode == "monolithic"

    if monolithic:
        items, all_skills = _monolithic_items()
    else:
        items, all_skills = _tier1_items(), []
    prefix_tokens = sum(item.tokens for item in items)  # tout ce qui précède la conversation

    active = []            # skills actifs (mode progressif), du plus ancien au plus récent
    added_sources = set()  # chemins des AGENTS.md déjà ajoutés (évite les doublons)
    loaded = set()         # chemins des références déjà chargées
    evictions = []         # ce qui a été retiré, dans l'ordre ("unloaded:...", "deactivated:...")

    for event in events:
        keep_source = ""   # bloc ajouté par cet événement et protégé de l'éviction
        if event.kind in CONVERSATION_PREFIXES:
            items.append(_conversation_item(event))
        elif event.kind == "activate_skill":
            if monolithic:
                _find_skill(event.skill)  # tout est déjà chargé : on vérifie seulement le nom
            else:
                _activate_skill(event.skill, items, active, added_sources, loaded, evictions)
        elif event.kind == "load_reference":
            if not monolithic:  # en monolithique, les références ne sont pas chargées (contrat)
                new_items = _reference_items(event.skill, event.filename, active, loaded)
                items.extend(new_items)
                if new_items:
                    keep_source = new_items[0].source
        elif event.kind in NOT_IMPLEMENTED_KINDS:
            raise NotImplementedError(f"événement '{event.kind}' pas encore implémenté")
        else:
            raise ValueError(f"type d'événement inconnu : '{event.kind}'")

        if not monolithic:  # pas d'éviction en monolithique : le budget peut être dépassé
            _enforce_budget(items, active, added_sources, loaded, evictions, budget, keep_source)

    if monolithic:
        # Tous les skills et tous les outils sont considérés comme actifs.
        tools = list(Tool.objects.all())
        active_names = [s.name for s in all_skills]
        allowed_tools = [t.name for t in tools]
        tool_tokens = sum(t.tokens for t in tools)
    else:
        active_names = [s.name for s in active]
        allowed_tools = _allowed_tools(active)
        tool_tokens = _tool_tokens(allowed_tools)

    return CompileResult(
        text=SEPARATOR.join(item.text for item in items),
        items=items,
        tokens=sum(item.tokens for item in items) + tool_tokens,
        budget=budget,
        prefix_tokens=prefix_tokens,
        active_skills=active_names,
        allowed_tools=allowed_tools,
        tool_tokens=tool_tokens,
        compacted=bool(evictions),  # True dès qu'un bloc a été retiré
        evictions=evictions,
    )