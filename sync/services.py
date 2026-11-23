"""Service de synchronisation : quand la documentation change sur GitHub, on met la base à jour.

    GitHub (push) --webhook--> Django /api/sync/github/   (signature HMAC vérifiée)
    GitHub (push) --webhook--> n8n --> Django /api/sync/n8n/   (jeton partagé vérifié)
puis : git pull (si SYNC_GIT_PULL=1) et registry.loader.index_all().
Le compilateur relit la base à chaque appel : rien d'autre à faire.
"""

import hashlib
import hmac
import subprocess

from django.conf import settings

from registry.loader import index_all

from .models import SyncEvent


def valid_signature(secret: str, body: bytes, header: str) -> bool:
    """GitHub envoie « sha256=<HMAC du corps avec le secret> » dans X-Hub-Signature-256."""
    if not secret or not header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)   # comparaison à temps constant


def run_sync(source: str, ref: str = "", commit: str = "") -> SyncEvent:
    """git pull (facultatif), réindexation du registre, puis enregistrement d'un SyncEvent."""
    event = SyncEvent(source=source, ref=ref, commit=commit)
    try:
        if settings.SYNC_GIT_PULL:
            subprocess.run(["git", "pull", "--ff-only"], cwd=settings.BASE_DIR,
                           check=True, capture_output=True, timeout=120)
        summary = index_all()
        event.status = "ok"
        event.message = f"registre réindexé : {summary['counts']}"
    except Exception as exc:     # git pull raté, ou fichier YAML invalide
        event.status, event.message = "error", str(exc)
    event.save()
    return event
