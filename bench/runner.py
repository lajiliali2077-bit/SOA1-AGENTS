"""Jouer une requête prédéfinie (tous ses tours), l'enregistrer en base, prévenir n8n."""

import time

import requests
from django.conf import settings

from compiler.core import Event
from erp.seed import seed_demo

from .checks import evaluate
from .llm import GeminiClient
from .loop import run_turn
from .models import Run


def run_task(task, mode="progressive", client=None) -> Run:
    client = client or GeminiClient()
    seed_demo()                      # chaque exécution repart des mêmes données du mini-ERP
    start = time.time()
    events, turns = [], []
    for turn in task.turns:
        events.append(Event(kind="user", text=turn.user))
        result = run_turn(events, client, mode=mode, budget=settings.TOKEN_BUDGET,
                          confirmed=turn.confirmed)
        turns.append(result)
        if result.error:
            break

    steps = [s for t in turns for s in t.steps if s.action != "error"]
    run = Run(
        task_id=task.id, title=task.title, mode=mode, client=client.name, model=client.model,
        turns=[t.to_dict() for t in turns],
        violations=[v for t in turns for v in t.violations],
        answer=turns[-1].answer,
        llm_calls=len(steps),
        prog_tokens=sum(s.prog_tokens for s in steps),
        mono_tokens=sum(s.mono_tokens for s in steps),
        input_tokens=sum(s.usage.get("input", 0) for s in steps),
        output_tokens=sum(s.usage.get("output", 0) for s in steps),
        thinking_tokens=sum(s.usage.get("thinking", 0) for s in steps),
        duration_s=round(time.time() - start, 1),
        error=" ; ".join(t.error for t in turns if t.error),
    )
    run.checks = evaluate(task, turns)
    run.passed = all(c["passed"] for c in run.checks) and not run.error and not run.violations
    run.save()
    notify_n8n(run)
    return run


def notify_n8n(run: Run):
    """Webhook sortant (facultatif) : on envoie le résumé de l'exécution à n8n."""
    if not settings.N8N_RUN_WEBHOOK_URL:
        return
    try:
        requests.post(settings.N8N_RUN_WEBHOOK_URL, json=run.summary(), timeout=5)
    except requests.RequestException:
        pass                         # n8n arrêté : l'exécution reste enregistrée
