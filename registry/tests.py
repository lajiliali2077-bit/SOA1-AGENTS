"""Tests du registre : lecture des fichiers et validation des skills."""

from django.test import TestCase

from .loader import check_skill, count_tokens, department_tokens, index_all, read_tools
from .models import AgentsFile, Skill, Tool


class RegistryTests(TestCase):
    def test_indexation_du_depot(self):
        summary = index_all()
        self.assertEqual(summary["counts"], {"tools": 21, "skills": 12, "agents": 13})
        self.assertEqual(summary["rejected"], {})
        self.assertEqual(Skill.objects.get(name="invoice-validation").status, "needs_review")
        self.assertEqual(AgentsFile.objects.get(level=1).path, "AGENTS.md")

    def test_relancer_ne_cree_pas_de_doublon(self):
        index_all()
        index_all()
        self.assertEqual(Skill.objects.count(), 12)

    def test_departement_finance_dans_les_criteres(self):
        index_all()
        size = department_tokens("finance")
        self.assertTrue(5500 <= size["total"] <= 7500, size)
        self.assertEqual(Tool.objects.filter(owner="finance").count(), 12)

    def test_regles_de_validation(self):
        tools = read_tools()
        skill = {"department": "finance", "allowed_tools": ["get_invoice"],
                 "description": "Check invoices. Use when asked.", "body": "Call get_invoice.",
                 "body_tokens": 10}
        self.assertEqual(check_skill(skill, tools), ("active", []))
        self.assertEqual(check_skill({**skill, "allowed_tools": ["outil_imaginaire"]}, tools)[0], "rejected")
        self.assertEqual(check_skill({**skill, "description": "Check invoices."}, tools)[0], "needs_review")

    def test_count_tokens(self):
        self.assertEqual(count_tokens(""), 0)
        self.assertGreater(count_tokens("Bonjour tout le monde"), 2)
