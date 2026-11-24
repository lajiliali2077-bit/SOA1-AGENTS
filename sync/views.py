"""Service Synchronisation (API REST avec Django REST Framework).

POST /api/sync/github/  webhook appelé par GitHub, signé avec GITHUB_WEBHOOK_SECRET
POST /api/sync/n8n/     appelé par le workflow n8n, qui relaie la requête GitHub telle quelle :
                        en-tête X-Sync-Token = N8N_SYNC_TOKEN et signature GitHub valide exigés
GET  /api/sync/events/  historique des synchronisations
"""

import hmac
import json

from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import SyncEvent
from .services import run_sync, valid_signature


def handle_github_event(request, source):
    """Vérifie la signature GitHub puis resynchronise sur un push de la branche suivie."""
    # 1. Sécurité : on vérifie la signature sur le corps brut, avant de lire le JSON.
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not valid_signature(settings.GITHUB_WEBHOOK_SECRET, request.body, signature):
        return Response({"error": "signature invalide"}, status=403)

    # 2. On ne réagit qu'à un push sur la branche suivie.
    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type == "ping":
        return Response({"status": "pong"})
    payload = json.loads(request.body or b"{}")
    ref = payload.get("ref", "")
    if event_type != "push" or ref != f"refs/heads/{settings.SYNC_BRANCH}":
        return Response({"status": "ignored", "ref": ref}, status=202)

    # 3. Resynchronisation.
    event = run_sync(source, ref=ref, commit=payload.get("after", "")[:64])
    return Response(event.to_dict(), status=200 if event.status == "ok" else 500)


@api_view(["POST"])
def github_webhook(request):
    return handle_github_event(request, "github")


@api_view(["POST"])
def n8n_trigger(request):
    """n8n relaie la requête GitHub telle quelle (corps brut + en-têtes GitHub).
    Double contrôle : le jeton prouve que l'appel vient de n8n, la signature HMAC
    prouve que le contenu vient de GitHub."""
    token = request.headers.get("X-Sync-Token", "")
    if not settings.N8N_SYNC_TOKEN or not hmac.compare_digest(settings.N8N_SYNC_TOKEN, token):
        return Response({"error": "jeton invalide"}, status=403)
    return handle_github_event(request, "n8n")


@api_view(["GET"])
def events(request):
    return Response({"events": [e.to_dict() for e in SyncEvent.objects.all()[:20]]})
