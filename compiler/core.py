"""Progressive Context Compiler : choisit ce qu'on envoie à l'IA pour une tâche.

Mode "progressive" (notre solution), divulgation progressive en 3 niveaux :
    Niveau 1 : AGENTS.md global + liste des skills (nom et description)      -> toujours
    Niveau 2 : AGENTS.md du département et du sous-domaine + corps du skill  -> quand l'IA active le skill
    Niveau 3 : fichier du dossier references/ du skill                       -> quand l'IA le demande
Puis on respecte le budget de tokens :
    1. masquer les anciennes sorties d'outils (dès 70 % du budget)
    2. retirer les références, la plus ancienne d'abord
    3. désactiver le skill le plus ancien (on en garde toujours au moins un)

Mode "monolithic" (pour comparer) : on envoie tout, tout le temps, sans budget.
"""

import json
from dataclasses import dataclass, field

from django.conf import settings

from masking.services import mask_observations
from registry.loader import count_tokens
from registry.models import AgentsFile, Skill, Tool

MAX_ACTIVE_SKILLS = 2


@dataclass(frozen=True)
class Event:
    """Un élément de l'historique de la conversation."""
    kind: str            # user | assistant | activate_skill | load_reference | observation
    text: str = ""       # message, ou sortie complète d'un outil
    skill: str = ""      # pour activate_skill et load_reference
    filename: str = ""   # pour load_reference
    tool: str = ""       # pour observation
    obs_id: str = ""     # pour observation


@dataclass
class Block:
    """Un morceau du contexte compilé."""
    kind: str            # agents | index | skill | reference | user | assistant | observation | masked
    text: str
    source: str = ""     # chemin du fichier, nom du skill ou obs_id
    tokens: int = 0

    def __post_init__(self):
        if not self.tokens:
            self.tokens = count_tokens(self.text)


@dataclass
class CompileResult:
    text: str                  # contexte envoyé à l'IA
    tokens: int                # total : texte + définitions des outils autorisés
    budget: int
    blocks: list
    active_skills: list
    allowed_tools: list
    tool_tokens: int
    evictions: list = field(default_factory=list)   # ex. "masked:obs-0003", "unloaded:...", "deactivated:..."

    @property
    def compacted(self) -> bool:
        return bool(self.evictions)

    def to_dict(self) -> dict:
        return {"text": self.text, "tokens": self.tokens, "budget": self.budget,
                "active_skills": self.active_skills, "allowed_tools": self.allowed_tools,
                "tool_tokens": self.tool_tokens, "evictions": self.evictions,
                "compacted": self.compacted,
                "blocks": [{"kind": b.kind, "source": b.source, "tokens": b.tokens}
                           for b in self.blocks]}


# ----- Petites fonctions utiles -----

def find_skill(name: str) -> Skill:
    skill = Skill.objects.filter(name=name).first()
    if skill is None:
        raise ValueError(f"skill inconnu : '{name}'")
    return skill


def allowed_tools(skills: list) -> list:
    names = []
    for skill in skills:
        for tool in skill.allowed_tools:
            if tool not in names:
                names.append(tool)
    return names


def tools_block(names: list) -> Block:
    """Définitions des outils autorisés, envoyées à l'IA pour qu'elle sache comment les appeler."""
    lines = ["Outils autorisés (action call_tool, arguments_json = objet JSON des paramètres) :"]
    for tool in Tool.objects.filter(name__in=names):
        lines.append(json.dumps({"name": tool.name, "mode": tool.mode, "description": tool.description,
                                 "parameters": tool.parameters}, ensure_ascii=False))
    return Block("tools", "\n".join(lines), source="tools")


def tool_tokens(names: list) -> int:
    return tools_block(names).tokens if names else 0


def conversation_block(event: Event) -> Block:
    if event.kind == "user":
        return Block("user", f"Utilisateur : {event.text}")
    if event.kind == "assistant":
        return Block("assistant", f"Assistant : {event.text}")
    return Block("observation", f"Observation ({event.tool}, {event.obs_id}) :\n{event.text}",
                 source=event.obs_id)


def skill_index() -> str:
    lines = ["Skills disponibles (activez-en un pour lire sa procédure) :"]
    for s in Skill.objects.all():
        lines.append(f"- {s.name} ({s.department}) : {s.description}")
    return "\n".join(lines)


def reference_block(skill: Skill, filename: str) -> Block:
    """Niveau 3 : un fichier du dossier references/ du skill, et seulement de ce dossier."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError(f"nom de fichier interdit : '{filename}'")
    path = settings.BASE_DIR / skill.path.replace("SKILL.md", "references") / filename
    if not path.is_file():
        raise ValueError(f"référence introuvable : {skill.name}/{filename}")
    content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return Block("reference", f"Référence : {skill.name}/{filename}\n\n{content}",
                 source=f"{skill.name}/{filename}")


def remove_skill(blocks: list, skill: Skill) -> list:
    """Retire le corps d'un skill et ses références (ses AGENTS.md restent)."""
    return [b for b in blocks
            if not (b.kind == "skill" and b.source == skill.name)
            and not (b.kind == "reference" and b.source.startswith(skill.name + "/"))]


CONVERSATION = ("user", "assistant", "observation", "masked")


def make_result(blocks, budget, skills, tools, evictions) -> CompileResult:
    """Ordre du texte envoyé : règles et skills, puis outils autorisés, puis la conversation."""
    rules = [b for b in blocks if b.kind not in CONVERSATION]
    conversation = [b for b in blocks if b.kind in CONVERSATION]
    if tools:
        rules.append(tools_block(tools))
    blocks = rules + conversation
    return CompileResult(
        text="\n\n".join(b.text for b in blocks),
        tokens=sum(b.tokens for b in blocks),
        budget=budget, blocks=blocks, active_skills=[s.name for s in skills],
        allowed_tools=tools, tool_tokens=tool_tokens(tools), evictions=evictions)


# ----- Le compilateur -----

def compile_context(events: list, budget: int = 6000, mode: str = "progressive") -> CompileResult:
    if mode == "monolithic":
        return compile_monolithic(events, budget)
    if mode != "progressive":
        raise ValueError(f"mode inconnu : '{mode}'")

    # Niveau 1 : toujours présent
    blocks = [Block("agents", a.content, a.path) for a in AgentsFile.objects.filter(level=1)]
    blocks.append(Block("index", skill_index()))
    active = []        # skills actifs, du plus ancien au plus récent
    evictions = []

    for event in events:
        if event.kind in ("user", "assistant", "observation"):
            blocks.append(conversation_block(event))

        elif event.kind == "activate_skill":         # Niveau 2
            skill = find_skill(event.skill)
            if skill in active:
                continue
            if len(active) == MAX_ACTIVE_SKILLS:      # 2 skills maximum
                oldest = active.pop(0)
                blocks = remove_skill(blocks, oldest)
                evictions.append(f"deactivated:{oldest.name}")
            active.append(skill)
            # Règles du département puis du sous-domaine : la plus proche est la dernière lue
            department_rules = AgentsFile.objects.filter(level=2, department=skill.department)
            subdomain_rules = AgentsFile.objects.filter(level=3, department=skill.department,
                                                        subdomain=skill.subdomain)
            for agents in list(department_rules) + list(subdomain_rules):
                if agents.path not in [b.source for b in blocks]:
                    blocks.append(Block("agents", agents.content, agents.path))
            blocks.append(Block("skill", f"Skill activé : {skill.name}\n\n{skill.body}", skill.name))

        elif event.kind == "load_reference":         # Niveau 3
            skill = None
            for s in active:
                if s.name == event.skill:
                    skill = s
            if skill is None:
                raise ValueError(f"activez le skill '{event.skill}' avant de lire ses références")
            block = reference_block(skill, event.filename)
            if block.source not in [b.source for b in blocks]:
                blocks.append(block)
        else:
            raise ValueError(f"type d'événement inconnu : '{event.kind}'")

    # Budget de tokens
    def total():
        return sum(b.tokens for b in blocks) + tool_tokens(allowed_tools(active))

    # 1. masquage des anciennes sorties d'outils
    blocks, masked = mask_observations(blocks, budget, tool_tokens(allowed_tools(active)))
    evictions += [f"masked:{obs_id}" for obs_id in masked]
    # 2. références, la plus ancienne d'abord
    references = [b for b in blocks if b.kind == "reference"]
    while total() > budget and references:
        oldest = references.pop(0)
        blocks.remove(oldest)
        evictions.append(f"unloaded:{oldest.source}")
    # 3. skill le plus ancien (on garde toujours le plus récent)
    while total() > budget and len(active) > 1:
        oldest = active.pop(0)
        blocks = remove_skill(blocks, oldest)
        evictions.append(f"deactivated:{oldest.name}")

    return make_result(blocks, budget, active, allowed_tools(active), evictions)


def compile_monolithic(events: list, budget: int) -> CompileResult:
    """Tout est chargé : tous les AGENTS.md, tous les skills et leurs références, tous les outils.
    Aucune éviction, aucun masquage."""
    blocks = [Block("agents", a.content, a.path) for a in AgentsFile.objects.all()]
    skills = list(Skill.objects.all())
    for s in skills:
        blocks.append(Block("skill", f"Skill : {s.name}\n\n{s.body}", s.name))
        folder = settings.BASE_DIR / s.path.replace("SKILL.md", "references")
        for path in sorted(folder.glob("*.md")):
            blocks.append(reference_block(s, path.name))
    for event in events:
        if event.kind in ("user", "assistant", "observation"):
            blocks.append(conversation_block(event))
        elif event.kind == "activate_skill":
            find_skill(event.skill)        # déjà chargé : on vérifie seulement qu'il existe
        elif event.kind != "load_reference":
            raise ValueError(f"type d'événement inconnu : '{event.kind}'")
    all_tools = list(Tool.objects.values_list("name", flat=True))
    return make_result(blocks, budget, skills, all_tools, [])
