"""Tests de la synchronisation : webhook GitHub signé et appel n8n."""

import hashlib
import hmac
import json

from django.test import TestCase, override_settings

from registry.models import Skill

from .models import SyncEvent

SECRET = "secret-de-test"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


@override_settings(GITHUB_WEBHOOK_SECRET=SECRET, N8N_SYNC_TOKEN="jeton", SYNC_GIT_PULL=False)
class SyncTests(TestCase):
    def github(self, payload, signature=None, event="push"):
        body = json.dumps(payload).encode()
        return self.client.post("/api/sync/github/", body, content_type="application/json",
                                headers={"X-GitHub-Event": event,
                                         "X-Hub-Signature-256": signature or sign(body)})

    def test_push_signe_sur_main(self):
        response = self.github({"ref": "refs/heads/main", "after": "abc123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Skill.objects.count(), 6)            # base resynchronisée
        self.assertEqual(SyncEvent.objects.get().commit, "abc123")

    def test_fausse_signature_refusee(self):
        self.assertEqual(self.github({"ref": "refs/heads/main"}, signature="sha256=faux").status_code, 403)
        self.assertEqual(SyncEvent.objects.count(), 0)

    def test_ping_et_autre_branche(self):
        self.assertEqual(self.github({}, event="ping").json()["status"], "pong")
        self.assertEqual(self.github({"ref": "refs/heads/dev"}).status_code, 202)
        self.assertEqual(Skill.objects.count(), 0)

    def n8n(self, token, signature=None, event="push"):
        body = json.dumps({"ref": "refs/heads/main", "after": "def456"}).encode()
        return self.client.post("/api/sync/n8n/", body, content_type="application/json",
                                headers={"X-Sync-Token": token, "X-GitHub-Event": event,
                                         "X-Hub-Signature-256": signature or sign(body)})

    def test_n8n(self):
        self.assertEqual(self.n8n("faux").status_code, 403)                          # mauvais jeton
        self.assertEqual(self.n8n("jeton", signature="sha256=faux").status_code, 403)  # fausse signature
        self.assertEqual(SyncEvent.objects.count(), 0)
        self.assertEqual(self.n8n("jeton", event="ping").json()["status"], "pong")
        good = self.n8n("jeton")
        self.assertEqual(good.status_code, 200)
        self.assertEqual(good.json()["source"], "n8n")
        self.assertEqual(SyncEvent.objects.get().commit, "def456")
