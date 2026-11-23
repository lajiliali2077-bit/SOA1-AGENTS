"""Tests de l'agent : format des réponses de l'IA, boucle gouvernée, tâches, API, client Gemini."""

import json
from types import SimpleNamespace

from django.test import TestCase, override_settings

from compiler.core import Event
from registry.loader import index_all

from .llm import GeminiClient, LLMError, ScriptedClient, make_client
from .loop import run_turn
from .runner import run_task
from .schemas import StepError, parse_step
from .tasks import load_tasks


class SchemaTests(TestCase):
    def test_reponses_valides(self):
        self.assertEqual(parse_step('{"action": "answer", "text": "ok"}').text, "ok")
        step = parse_step('{"action": "call_tool", "tool": "get_invoice", '
                          '"arguments_json": "{\\"invoice_id\\": \\"INV-1\\"}"}')
        self.assertEqual(step.arguments, {"invoice_id": "INV-1"})

    def test_reponses_refusees(self):
        for raw in ["pas du json", '{"action": "tout_supprimer"}', '{"action": "answer"}',
                    '{"action": "call_tool", "tool": "x", "pirate": 1}',
                    '{"action": "load_reference", "skill": "a", "filename": "../secret"}',
                    '{"action": "call_tool", "tool": "x", "arguments_json": "[1]"}']:
            with self.subTest(raw=raw), self.assertRaises(StepError):
                parse_step(raw)


class AgentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        index_all()

    def test_les_7_taches_reussissent_hors_ligne(self):
        tasks = load_tasks()
        self.assertEqual(len(tasks), 7)
        for task in tasks:
            with self.subTest(task=task.id):
                run = run_task(task, client_kind="scripted")
                self.assertTrue(run.passed, (run.checks, run.violations, run.error))

    def test_ecriture_bloquee_sans_confirmation(self):
        client = ScriptedClient([
            {"action": "activate_skill", "skill": "invoice-validation"},
            {"action": "call_tool", "tool": "update_invoice_status",
             "arguments": {"invoice_id": "INV-2026-00512", "new_status": "approved",
                           "reason": "ok", "approver_id": "U-014"}},
            {"action": "answer", "text": "Decision: HOLD\nSkill used: invoice-validation"},
        ])
        turn = run_turn([Event(kind="user", text="Approuve INV-2026-00512")], client)
        self.assertEqual(turn.steps[1].guard, "confirmation_required")
        self.assertEqual(turn.violations, [])

    def test_reponse_invalide_et_outil_sans_skill(self):
        client = ScriptedClient([
            "ceci n'est pas du JSON",
            {"action": "call_tool", "tool": "get_invoice", "arguments": {"invoice_id": "X"}},
            {"action": "answer", "text": "Je ne sais pas."},
        ])
        turn = run_turn([Event(kind="user", text="Bonjour")], client)
        self.assertEqual([s.action for s in turn.steps], ["invalid", "call_tool", "answer"])
        self.assertEqual(turn.steps[1].guard, "skill_not_active")
        self.assertEqual(len(turn.violations), 1)     # pas de ligne « Skill used: »

    @override_settings(GEMINI_API_KEY="")
    def test_client_auto_sans_cle_utilise_le_plan_b(self):
        self.assertEqual(make_client("auto", "fin-01").name, "scripted")
        with self.assertRaises(LLMError):
            make_client("gemini")


class GeminiTests(TestCase):
    def test_appel_gemini_simule(self):
        """On remplace le SDK Google par un faux objet : aucun appel réseau."""
        sent = []

        class FakeModels:
            def generate_content(self, model, contents, config):
                sent.append(config)
                return SimpleNamespace(text='{"action": "answer", "text": "prêt"}')

        client = GeminiClient(client=SimpleNamespace(models=FakeModels()))
        self.assertEqual(parse_step(client.next_step("contexte")).text, "prêt")
        self.assertEqual(sent[0].response_mime_type, "application/json")


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        index_all()

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")

    def test_api(self):
        self.assertEqual(len(self.client.get("/api/skills/").json()["skills"]), 12)
        self.assertGreater(self.post("/api/tokens/", {"text": "Bonjour tout le monde"}).json()["tokens"], 2)
        result = self.post("/api/compile/", {"events": [
            {"kind": "user", "text": "Bonjour"},
            {"kind": "activate_skill", "skill": "vendor-check"}]}).json()
        self.assertEqual(result["active_skills"], ["vendor-check"])
        self.assertEqual(self.post("/api/compile/", {"mode": "autre"}).status_code, 400)
        self.assertTrue(self.post("/api/run/", {"task_id": "fin-05", "client": "scripted"}).json()["passed"])
        self.assertEqual(self.client.get("/api/runs/").status_code, 200)
        self.assertContains(self.client.get("/dashboard/"), "fin-05")

    @override_settings(GEMINI_API_KEY="")
    def test_message_libre_sans_cle(self):
        self.assertEqual(self.post("/api/run/", {"message": "Bonjour"}).status_code, 503)
