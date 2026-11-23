"""API REST (Django REST Framework) des services, et la page web.

Service Agent
    GET  /api/tasks/                  requêtes prédéfinies que l'utilisateur peut choisir
    POST /api/run/                    {"task_id": "fin-01", "mode": "progressive"} : Gemini l'exécute
    GET  /api/runs/                   dernières exécutions + statistiques du tableau de bord
    GET  /api/runs/<id>/              détail d'une exécution (chaque étape)
Service Compilateur
    POST /api/compile/                {"events": [...], "budget": 6000, "mode": "progressive"}
    POST /api/tokens/                 {"text": "..."} -> nombre de tokens (tiktoken)
Service Registre
    GET  /api/skills/                 liste des skills
Service Outils
    GET  /api/tools/                  catalogue des outils (tools/*.yaml)
    POST /api/tools/<nom>/            exécute un outil de lecture : {"arguments": {...}}
Service Masquage
    GET  /api/observations/<obs_id>/  sortie complète d'une observation masquée
Page web
    GET  /                            interface (exécuter + tableau de bord)
"""

from django.db.models import Sum
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response

from compiler.core import Event, compile_context
from engine.executor import execute_tool
from engine.guard import argument_problem
from masking.services import recall_observation
from registry.loader import count_tokens
from registry.models import Skill, Tool

from .llm import LLMError
from .models import Run
from .runner import run_task
from .tasks import get_task, load_tasks


# ----- Service Agent -----

@api_view(["GET"])
def tasks(request):
    return Response({"tasks": [t.summary() for t in load_tasks()]})


@api_view(["POST"])
def run_view(request):
    mode = request.data.get("mode", "progressive")
    if mode not in ("progressive", "monolithic"):
        return Response({"error": "mode : progressive ou monolithic"}, status=400)
    try:
        task = get_task(request.data.get("task_id", ""))
        run = run_task(task, mode=mode)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    except LLMError as exc:
        return Response({"error": str(exc)}, status=503)
    return Response(run.to_dict())


@api_view(["GET"])
def runs(request):
    """Les 30 dernières exécutions et les totaux du tableau de bord."""
    totals = Run.objects.filter(mode="progressive").aggregate(
        prog=Sum("prog_tokens"), mono=Sum("mono_tokens"))
    billed = Run.objects.aggregate(input=Sum("input_tokens"), output=Sum("output_tokens"),
                                   thinking=Sum("thinking_tokens"))
    prog, mono = totals["prog"] or 0, totals["mono"] or 0
    stats = {
        "runs": Run.objects.count(),
        "passed": Run.objects.filter(passed=True).count(),
        "prog_tokens": prog, "mono_tokens": mono,
        "saving_pct": round(100 * (mono - prog) / mono, 1) if mono else None,
        "billed": {k: v or 0 for k, v in billed.items()},
        "start_prog": compile_context([]).tokens,
        "start_mono": compile_context([], mode="monolithic").tokens,
    }
    return Response({"stats": stats, "runs": [r.summary() for r in Run.objects.all()[:30]]})


@api_view(["GET"])
def run_detail(request, run_id):
    run = Run.objects.filter(pk=run_id).first()
    if run is None:
        return Response({"error": "exécution inconnue"}, status=404)
    return Response(run.to_dict())


# ----- Service Compilateur et Registre -----

@api_view(["POST"])
def compile_view(request):
    try:
        events = [Event(**e) for e in request.data.get("events", [])]
        result = compile_context(events, budget=request.data.get("budget", 6000),
                                 mode=request.data.get("mode", "progressive"))
    except (ValueError, TypeError) as exc:
        return Response({"error": str(exc)}, status=400)
    return Response(result.to_dict())


@api_view(["POST"])
def tokens(request):
    return Response({"tokens": count_tokens(request.data.get("text", ""))})


@api_view(["GET"])
def skills(request):
    data = [{"name": s.name, "description": s.description, "department": s.department,
             "subdomain": s.subdomain, "status": s.status, "allowed_tools": s.allowed_tools,
             "index_tokens": s.index_tokens, "body_tokens": s.body_tokens}
            for s in Skill.objects.all()]
    return Response({"skills": data})


# ----- Service Outils -----

@api_view(["GET"])
def tools(request):
    data = [{"name": t.name, "mode": t.mode, "description": t.description, "parameters": t.parameters}
            for t in Tool.objects.all()]
    return Response({"tools": data})


@api_view(["POST"])
def tool_call(request, name):
    """Appel direct d'un outil par API (sans l'IA). Les outils d'écriture sont réservés à l'agent."""
    tool = Tool.objects.filter(name=name).first()
    if tool is None:
        return Response({"error": f"outil inconnu : {name}"}, status=404)
    if tool.mode == "write":
        return Response({"error": "outil d'écriture : passer par l'agent (confirmation obligatoire)"},
                        status=403)
    arguments = request.data.get("arguments", {})
    problem = argument_problem(arguments, tool.parameters)
    if problem:
        return Response({"error": problem}, status=400)
    return Response({"tool": name, "output": execute_tool(name, arguments)})


# ----- Service Masquage -----

@api_view(["GET"])
def observation(request, obs_id):
    try:
        return Response({"obs_id": obs_id, "output": recall_observation(obs_id)})
    except ValueError as exc:
        return Response({"error": str(exc)}, status=404)


# ----- Page web -----

def home(request):
    return render(request, "bench/app.html")
