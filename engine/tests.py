"""Tests du moteur déterministe : garde, exécuteur, vérificateur."""

from types import SimpleNamespace

from django.test import TestCase

from registry.loader import index_all

from .executor import execute_tool
from .guard import check_tool_call
from .verifier import verify_answer

INVOICE_SKILL = SimpleNamespace(
    active_skills=["invoice-validation"],
    allowed_tools=["get_invoice", "get_vendor", "update_invoice_status"])
WRITE = {"invoice_id": "INV-2026-00512", "new_status": "approved", "reason": "ok", "approver_id": "U-014"}


class GuardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        index_all()

    def code(self, tool, arguments, context=INVOICE_SKILL, confirmed=False):
        return check_tool_call(tool, arguments, context, confirmed).code

    def test_codes_de_la_garde(self):
        no_skill = SimpleNamespace(active_skills=[], allowed_tools=[])
        self.assertEqual(self.code("get_invoice", {"invoice_id": "X"}, no_skill), "skill_not_active")
        self.assertEqual(self.code("get_bank_balance", {"account_id": "A"}), "tool_not_allowed")
        self.assertEqual(self.code("get_invoice", {}), "bad_arguments")                    # manquant
        self.assertEqual(self.code("get_invoice", {"invoice_id": 12}), "bad_arguments")    # type
        self.assertEqual(self.code("get_invoice", {"invoice_id": "X", "pirate": 1}), "bad_arguments")
        self.assertEqual(self.code("update_invoice_status", {**WRITE, "new_status": "paid"}), "bad_arguments")
        self.assertEqual(self.code("get_invoice", {"invoice_id": "X"}), "ok")

    def test_ecriture_seulement_apres_confirmation(self):
        self.assertEqual(self.code("update_invoice_status", WRITE), "confirmation_required")
        self.assertEqual(self.code("update_invoice_status", WRITE, confirmed=True), "ok")


class ExecutorTests(TestCase):
    def test_fixtures(self):
        self.assertIn("Atlas", execute_tool("finance", "get_vendor", {"vendor_id": "V-00118"}))
        self.assertEqual(execute_tool("finance", "get_vendor", {"vendor_id": "V-99999"}), "Vendor not found.")
        with self.assertRaises(ValueError):
            execute_tool("hr", "get_vendor", {})


class VerifierTests(TestCase):
    def test_reponse_conforme(self):
        text = "Decision: HOLD\nAmount: 6 200.000 TND\nSkill used: invoice-validation"
        self.assertEqual(verify_answer(text, ["invoice-validation"]), [])
        self.assertEqual(verify_answer("Voir le service RH.\nSkill used: none", []), [])

    def test_reponses_refusees(self):
        def codes(text, skills):
            return [p.split(":")[0] for p in verify_answer(text, skills)]
        self.assertEqual(codes("Decision: HOLD", ["invoice-validation"]), ["skill_line"])
        self.assertEqual(codes("Skill used: none", ["vendor-check"]), ["skill_line"])
        self.assertEqual(codes("IBAN TN59 1000 6035 1835 9847 8831\nSkill used: none", []), ["iban"])
        self.assertEqual(codes("Decision: MAYBE\nSkill used: invoice-validation", ["invoice-validation"]),
                         ["decision"])
