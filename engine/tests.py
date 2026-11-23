"""Tests du moteur déterministe : garde et vérificateur."""

from types import SimpleNamespace

from django.test import TestCase

from registry.loader import index_all

from .guard import check_tool_call
from .verifier import verify_answer

RETURN_SKILL = SimpleNamespace(active_skills=["return-request"],
                               allowed_tools=["get_order", "get_refunds", "create_refund"])
WRITE = {"order_id": "CMD-2026-0512", "amount_tnd": 119.0, "reason": "taille", "approved_by": "A-03"}


class GuardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        index_all()

    def code(self, tool, arguments, context=RETURN_SKILL, confirmed=False):
        return check_tool_call(tool, arguments, context, confirmed).code

    def test_codes_de_la_garde(self):
        no_skill = SimpleNamespace(active_skills=[], allowed_tools=[])
        self.assertEqual(self.code("get_order", {"order_id": "X"}, no_skill), "skill_not_active")
        self.assertEqual(self.code("track_shipment", {"order_id": "X"}), "tool_not_allowed")
        self.assertEqual(self.code("get_order", {}), "bad_arguments")                    # manquant
        self.assertEqual(self.code("get_order", {"order_id": 12}), "bad_arguments")      # type
        self.assertEqual(self.code("get_order", {"order_id": "X", "pirate": 1}), "bad_arguments")
        self.assertEqual(self.code("get_order", {"order_id": "X"}), "ok")

    def test_ecriture_seulement_apres_confirmation(self):
        self.assertEqual(self.code("create_refund", WRITE), "confirmation_required")
        self.assertEqual(self.code("create_refund", WRITE, confirmed=True), "ok")


class VerifierTests(TestCase):
    def test_reponse_conforme(self):
        text = "Decision: HOLD\nAmount: 349.000 TND\nSkill used: return-request"
        self.assertEqual(verify_answer(text, ["return-request"]), [])
        self.assertEqual(verify_answer("Voir le service RH.\nSkill used: none", []), [])

    def test_reponses_refusees(self):
        def codes(text, skills):
            return [p.split(":")[0] for p in verify_answer(text, skills)]
        self.assertEqual(codes("Decision: HOLD", ["return-request"]), ["skill_line"])
        self.assertEqual(codes("Skill used: none", ["order-tracking"]), ["skill_line"])
        self.assertEqual(codes("Écrire à salma.benali@example.com\nSkill used: none", []), ["email"])
        self.assertEqual(codes("Decision: MAYBE\nSkill used: return-request", ["return-request"]), ["decision"])
