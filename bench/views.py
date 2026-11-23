"""API JSON (sans Django REST Framework) et tableau de bord.

POST /api/tokens/                  {"text": "..."} -> nombre de tokens
GET  /api/skills/                  liste des skills
POST /api/compile/                 {"events": [...], "budget": 6000, "mode": "progressive"}
POST /api/run/                     {"task_id": "fin-01", "mode": "progressive", "client": "scripted"}
                                   ou {"message": "Valide INV-2026-00457", "client": "gemini"}
GET  /api/runs/                    dernières exécutions
GET  /api/observations/<obs_id>/   sortie complète d'une observation masquée
GET  /dashboard/                   tableau de bord
"""

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from compiler.core import Event, compile_context
from masking.services import recall_observation
from registry.loader import count_tokens
from registry.models import Skill
from sync.models import SyncEvent

from .llm import LLMError
from .models import Run
from .runner import run_message, run_task
from .tasks import get_task, load_tasks


@csrf_exempt
def tokens(request):
    """Service de comptage de tokens : {"text": "..."} -> {"tokens": 12}."""
    if request.method != "POST":
        return JsonResponse({"error": "POST attendu"}, status=405)
    text = json.loads(request.body).get("text", "")
    return JsonResponse({"tokens": count_tokens(text)})


def skills(request):
    data = []
    for s in Skill.objects.all():
        data.append({"name": s.name, "description": s.description, "department": s.department,
                     "subdomain": s.subdomain, "status": s.status,
                     "allowed_tools": s.allowed_tools, "index_tokens": s.index_tokens,
                     "body_tokens": s.body_tokens})
    return JsonResponse({"skills": data})


@csrf_exempt
def compile_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST attendu"}, status=405)
    try:
        data = json.loads(request.body)
        events = [Event(**e) for e in data.get("events", [])]
        result = compile_context(events, budget=data.get("budget", 6000),
                                 mode=data.get("mode", "progressive"))
    except (ValueError, TypeError, AttributeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(result.to_dict())


@csrf_exempt
def run_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST attendu"}, status=405)
    try:
        data = json.loads(request.body)
        mode = data.get("mode", "progressive")
        if data.get("task_id"):
            task = get_task(data["task_id"])
            run = run_task(task, client_kind=data.get("client", "auto"), mode=mode)
        elif data.get("message"):
            run = run_message(data["message"], client_kind=data.get("client", "gemini"),
                                 mode=mode, confirmed=data.get("confirmed") is True)
        else:
            return JsonResponse({"error": "'task_id' ou 'message' obligatoire"}, status=400)
    except (ValueError, AttributeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except LLMError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    return JsonResponse(run.to_dict())


def runs(request):
    data = [run.to_dict() for run in Run.objects.all()[:20]]
    return JsonResponse({"runs": data})


def observation(request, obs_id):
    try:
        return JsonResponse({"obs_id": obs_id, "output": recall_observation(obs_id)})
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=404)


def dashboard(request):
    """Pour chaque tâche : dernière exécution en mode progressif et en mode monolithique."""
    rows = []
    for task in load_tasks():
        prog = Run.objects.filter(task_id=task.id, mode="progressive").first()
        mono = Run.objects.filter(task_id=task.id, mode="monolithic").first()
        saving = None
        if prog and mono and mono.total_tokens:
            saving = round(100 * (mono.total_tokens - prog.total_tokens) / mono.total_tokens, 1)
        rows.append({"task": task, "prog": prog, "mono": mono, "saving": saving})

    return render(request, "bench/dashboard.html", {
        "rows": rows,
        "start_prog": compile_context([]).tokens,
        "start_mono": compile_context([], mode="monolithic").tokens,
        "runs": Run.objects.all()[:10],
        "syncs": SyncEvent.objects.all()[:10],
    })
