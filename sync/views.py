"""Points d'entrée de la synchronisation.

POST /api/sync/github/  appelé par GitHub, signé avec GITHUB_WEBHOOK_SECRET
POST /api/sync/n8n/     appelé par le workflow n8n, avec l'en-tête X-Sync-Token = N8N_SYNC_TOKEN
GET  /api/sync/events/  historique des synchronisations
"""

import hmac
import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import SyncEvent
from .services import run_sync, valid_signature


@csrf_exempt
@require_POST
def github_webhook(request):
    # 1. Sécurité : on vérifie la signature sur le corps brut, avant de lire le JSON.
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not valid_signature(settings.GITHUB_WEBHOOK_SECRET, request.body, signature):
        return JsonResponse({"error": "signature invalide"}, status=403)

    # 2. On ne réagit qu'à un push sur la branche suivie.
    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type == "ping":
        return JsonResponse({"status": "pong"})
    payload = json.loads(request.body or b"{}")
    ref = payload.get("ref", "")
    if event_type != "push" or ref != f"refs/heads/{settings.SYNC_BRANCH}":
        return JsonResponse({"status": "ignored", "ref": ref}, status=202)

    # 3. Resynchronisation.
    event = run_sync("github", ref=ref, commit=payload.get("after", "")[:64])
    return JsonResponse(event.to_dict(), status=200 if event.status == "ok" else 500)


@csrf_exempt
@require_POST
def n8n_trigger(request):
    token = request.headers.get("X-Sync-Token", "")
    if not settings.N8N_SYNC_TOKEN or not hmac.compare_digest(settings.N8N_SYNC_TOKEN, token):
        return JsonResponse({"error": "jeton invalide"}, status=403)
    payload = json.loads(request.body or b"{}")
    event = run_sync("n8n", ref=str(payload.get("ref", "")), commit=str(payload.get("commit", ""))[:64])
    return JsonResponse(event.to_dict(), status=200 if event.status == "ok" else 500)


@require_GET
def events(request):
    return JsonResponse({"events": [e.to_dict() for e in SyncEvent.objects.all()[:20]]})
