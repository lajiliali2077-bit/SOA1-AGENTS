"""Tests de l'agent : format des réponses de l'IA, boucle gouvernée, mesures, API, client Gemini.

Aucun appel réseau : ScriptedClient rejoue des actions écrites à l'avance, et le SDK Google
est remplacé par un faux objet.
"""

import json
from types import SimpleNamespace

from django.test import TestCase, override_settings

from compiler.core import Event
from erp.models import Refund
from registry.loader import index_all

from .llm import GeminiClient, LLMError, ScriptedClient
from .loop import run_turn
from .runner import run_task
from .schemas import StepError, parse_step
from .tasks import get_task, load_tasks

# Ce qu'un bon agent fait pour cs-02 (2 tours)
CS02 = [
    {"action": "activate_skill", "skill": "return-request"},
    {"action": "call_tool", "tool": "get_order", "arguments": {"order_id": "CMD-2026-0512"}},
    {"action": "call_tool", "tool": "create_refund",          # tentative sans confirmation : refusée
     "arguments": {"order_id": "CMD-2026-0512", "amount_tnd": 119.0, "reason": "taille", "approved_by": "A-03"}},
    {"action": "answer", "text": "Decision: APPROVE\nAmount: 119.000 TND\nPlease confirm.\nSkill used: return-request"},
    {"action": "call_tool", "tool": "create_refund",
     "arguments": {"order_id": "CMD-2026-0512", "amount_tnd": 119.0, "reason": "taille", "approved_by": "A-03"}},
    {"action": "answer", "text": "Refund saved.\nDecision: APPROVE\nSkill used: return-request"},
]


class SchemaTests(TestCase):
    def test_reponses_valides(self):
        self.assertEqual(parse_step('{"action": "answer", "text": "ok"}').text, "ok")
        step = parse_step('{"action": "call_tool", "tool": "get_order", '
                          '"arguments_json": "{\\"order_id\\": \\"CMD-1\\"}"}')
        self.assertEqual(step.arguments, {"order_id": "CMD-1"})

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

    def test_les_requetes_sont_valides(self):
        self.assertEqual(len(load_tasks()), 9)

    def test_ecriture_refusee_puis_acceptee(self):
        run = run_task(get_task("cs-02"), client=ScriptedClient(CS02))
        steps = run.turns[0]["steps"]
        self.assertEqual(steps[2]["guard"], "confirmation_required")
        self.assertEqual(run.turns[1]["steps"][0]["guard"], "ok")
        self.assertTrue(run.passed, (run.checks, run.violations, run.error))
        self.assertEqual(Refund.objects.filter(order__order_id="CMD-2026-0512").count(), 1)

    def test_mesure_progressif_contre_monolithique(self):
        run = run_task(get_task("cs-02"), client=ScriptedClient(CS02))
        self.assertGreater(run.mono_tokens, run.prog_tokens)
        first = run.turns[0]["steps"][0]
        self.assertGreater(first["mono_tokens"], 3 * first["prog_tokens"])   # au démarrage

    def test_reponse_invalide_et_outil_sans_skill(self):
        client = ScriptedClient([
            "ceci n'est pas du JSON",
            {"action": "call_tool", "tool": "get_order", "arguments": {"order_id": "X"}},
            {"action": "answer", "text": "Je ne sais pas."},
        ])
        turn = run_turn([Event(kind="user", text="Bonjour")], client)
        self.assertEqual([s.action for s in turn.steps], ["invalid", "call_tool", "answer"])
        self.assertEqual(turn.steps[1].guard, "skill_not_active")
        self.assertEqual(len(turn.violations), 1)     # pas de ligne « Skill used: »


class GeminiTests(TestCase):
    def test_appel_gemini_simule(self):
        """On remplace le SDK Google par un faux objet : aucun appel réseau."""
        sent = []

        class FakeModels:
            def generate_content(self, model, contents, config):
                sent.append(config)
                usage = SimpleNamespace(prompt_token_count=120, candidates_token_count=9,
                                        thoughts_token_count=None)
                return SimpleNamespace(text='{"action": "answer", "text": "prêt"}', usage_metadata=usage)

            def count_tokens(self, model, contents):
                return SimpleNamespace(total_tokens=42)

        client = GeminiClient(client=SimpleNamespace(models=FakeModels()))
        reply = client.next_step("contexte")
        self.assertEqual(parse_step(reply.text).text, "prêt")
        self.assertEqual(reply.usage, {"input": 120, "output": 9, "thinking": 0})
        self.assertEqual(client.count_tokens("contexte"), 42)
        self.assertEqual(sent[0].response_mime_type, "application/json")

    @override_settings(GEMINI_API_KEY="")
    def test_sans_cle(self):
        with self.assertRaises(LLMError):
            GeminiClient()


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        index_all()

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")

    def test_api(self):
        self.assertEqual(len(self.client.get("/api/skills/").json()["skills"]), 6)
        self.assertEqual(len(self.client.get("/api/tasks/").json()["tasks"]), 9)
        self.assertEqual(len(self.client.get("/api/tools/").json()["tools"]), 8)
        self.assertGreater(self.post("/api/tokens/", {"text": "Bonjour tout le monde"}).json()["tokens"], 2)
        result = self.post("/api/compile/", {"events": [
            {"kind": "user", "text": "Bonjour"}, {"kind": "activate_skill", "skill": "order-tracking"}]}).json()
        self.assertEqual(result["active_skills"], ["order-tracking"])
        self.assertEqual(self.post("/api/compile/", {"mode": "autre"}).status_code, 400)
        self.assertEqual(self.post("/api/run/", {"task_id": "cs-01", "mode": "autre"}).status_code, 400)
        self.assertEqual(self.client.get("/api/runs/").json()["stats"]["runs"], 0)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_service_outils(self):
        from erp.seed import seed_demo
        seed_demo()
        ok = self.post("/api/tools/get_order/", {"arguments": {"order_id": "CMD-2026-0457"}})
        self.assertIn("349", ok.json()["output"])
        self.assertEqual(self.post("/api/tools/create_refund/", {"arguments": {}}).status_code, 403)
        self.assertEqual(self.post("/api/tools/get_order/", {"arguments": {}}).status_code, 400)

    @override_settings(GEMINI_API_KEY="")
    def test_run_sans_cle(self):
        self.assertEqual(self.post("/api/run/", {"task_id": "cs-01"}).status_code, 503)
