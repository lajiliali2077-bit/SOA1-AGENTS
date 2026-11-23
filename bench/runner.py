"""Jouer une tâche complète (tous ses tours) ou un message libre, puis l'enregistrer en base."""

from django.conf import settings

from compiler.core import Event

from .checks import evaluate
from .llm import make_client
from .loop import run_turn
from .models import Run


def save_run(task_id, mode, client, turn_results) -> Run:
    """Calcule les mesures de tokens à partir des étapes jouées et enregistre le Run."""
    steps = [s for t in turn_results for s in t.steps if s.action != "error"]
    run = Run(
        task_id=task_id, mode=mode, client=client.name,
        turns=[t.to_dict() for t in turn_results],
        violations=[v for t in turn_results for v in t.violations],
        answer=turn_results[-1].answer,
        llm_calls=len(steps),
        total_tokens=sum(s.tokens for s in steps),
        peak_tokens=max([s.tokens for s in steps], default=0),
        error=" ; ".join(t.error for t in turn_results if t.error),
    )
    run.save()
    return run


def run_task(task, client_kind="auto", mode="progressive") -> Run:
    client = make_client(client_kind, task.id)
    events = []
    turn_results = []
    for turn in task.turns:
        events.append(Event(kind="user", text=turn.user))
        result = run_turn(events, client, mode=mode, budget=settings.TOKEN_BUDGET,
                          confirmed=turn.confirmed, tool_results=task.tool_results)
        turn_results.append(result)
        if result.error:
            break

    run = save_run(task.id, mode, client, turn_results)
    run.checks = evaluate(task, turn_results)
    run.passed = all(c["passed"] for c in run.checks) and not run.error and not run.violations
    run.save()
    return run


def run_message(message, client_kind="gemini", mode="progressive", confirmed=False):
    """Message libre (API). Il faut la vraie IA : le plan B ne connaît que les tâches."""
    client = make_client(client_kind)
    events = [Event(kind="user", text=message)]
    result = run_turn(events, client, mode=mode, budget=settings.TOKEN_BUDGET, confirmed=confirmed)
    return save_run("", mode, client, [result])
