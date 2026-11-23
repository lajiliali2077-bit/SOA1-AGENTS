"""Boucle d'un tour d'agent : l'IA propose, le moteur déterministe décide.

    1. compile_context   le compilateur prépare le contexte (seulement ce qui est utile)
    2. IA                propose UNE action en JSON
    3. parse_step        Pydantic vérifie le format
    4. check_tool_call   la garde vérifie skill actif, outil autorisé, arguments, confirmation
    5. execute_tool      l'outil simulé répond ; la sortie est enregistrée (masquage)
    6. verify_answer     le vérificateur contrôle la réponse finale
On recommence à l'étape 1 jusqu'à la réponse finale (10 étapes au maximum).
"""

from dataclasses import asdict, dataclass, field

from compiler.core import Event, compile_context
from engine.executor import execute_tool
from engine.guard import check_tool_call
from engine.verifier import verify_answer
from masking.services import record_observation
from registry.models import Tool

from .llm import LLMError
from .schemas import StepError, parse_step

MAX_STEPS = 10


@dataclass
class Step:
    """Ce qui s'est passé à une étape."""
    action: str          # activate_skill, load_reference, call_tool, answer, invalid, error
    detail: str          # nom du skill ou de l'outil, ou message d'erreur
    tokens: int          # taille du contexte envoyé à l'IA
    compacted: bool      # le compilateur a-t-il masqué ou retiré quelque chose ?
    guard: str = ""      # décision de la garde pour call_tool
    arguments: dict = field(default_factory=dict)


@dataclass
class TurnResult:
    answer: str = ""
    violations: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    error: str = ""

    def to_dict(self):
        return asdict(self)


def add_observation(events: list, tool: str, text: str):
    """Ajoute un résultat (sortie d'outil ou refus du moteur) à l'historique."""
    obs_id = record_observation(tool, text)
    events.append(Event(kind="observation", tool=tool, text=text, obs_id=obs_id))


def run_turn(events, client, mode="progressive", budget=6000, confirmed=False, tool_results=None):
    """Joue un tour. `events` contient déjà le message de l'utilisateur ; il est complété ici."""
    turn = TurnResult()

    for _ in range(MAX_STEPS):
        # 1. contexte compilé
        context = compile_context(events, budget=budget, mode=mode)
        step = Step(action="", detail="", tokens=context.tokens, compacted=context.compacted)
        turn.steps.append(step)

        # 2. l'IA propose une action
        try:
            raw = client.next_step(context.text)
        except LLMError as exc:
            step.action, step.detail, turn.error = "error", str(exc), str(exc)
            return turn

        # 3. vérification du format
        try:
            action = parse_step(raw)
        except StepError as exc:
            step.action, step.detail = "invalid", str(exc)
            add_observation(events, "engine", f"Réponse refusée par le moteur : {exc}")
            continue
        step.action = action.action

        # 6. réponse finale, contrôlée par le vérificateur
        if action.action == "answer":
            step.detail = "réponse finale"
            used = []     # skills activés par l'agent pendant la conversation
            for e in events:
                if e.kind == "activate_skill" and e.skill not in used:
                    used.append(e.skill)
            turn.answer = action.text
            turn.violations = verify_answer(action.text, used)
            events.append(Event(kind="assistant", text=action.text))
            return turn

        # activation d'un skill ou lecture d'une référence : le compilateur les valide
        if action.action in ("activate_skill", "load_reference"):
            new_event = Event(kind=action.action, skill=action.skill, filename=action.filename or "")
            step.detail = action.skill + (f"/{action.filename}" if action.filename else "")
            try:
                compile_context(events + [new_event], budget=budget, mode=mode)
                events.append(new_event)
            except ValueError as exc:
                step.guard = "refused"
                add_observation(events, "engine", f"Action refusée : {exc}")
            continue

        # 4. appel d'outil : la garde décide
        step.detail, step.arguments = action.tool, action.arguments
        decision = check_tool_call(action.tool, action.arguments, context, confirmed)
        step.guard = decision.code
        if not decision.allowed:
            add_observation(events, action.tool, f"Appel refusé ({decision.code}) : {decision.message}")
            continue

        # 5. exécution (fixtures/<département>.json)
        department = Tool.objects.get(name=action.tool).owner
        try:
            output = execute_tool(department, action.tool, action.arguments)
        except ValueError as exc:
            output = (tool_results or {}).get(action.tool) or f"Erreur de l'outil : {exc}"
        add_observation(events, action.tool, output)

    turn.error = f"pas de réponse finale après {MAX_STEPS} étapes"
    return turn
