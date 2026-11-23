"""Tests du registre : lecture des fichiers et validation des skills."""

from django.test import TestCase

from .loader import check_skill, count_tokens, department_tokens, index_all, read_tools
from .models import AgentsFile, Skill


class RegistryTests(TestCase):
    def test_indexation_du_depot(self):
        summary = index_all()
        self.assertEqual(summary["counts"], {"tools": 8, "skills": 6, "agents": 4})
        self.assertEqual(summary["rejected"], {})
        self.assertEqual(Skill.objects.get(name="return-request").status, "needs_review")  # outil d'écriture
        self.assertEqual(AgentsFile.objects.get(level=1).path, "AGENTS.md")

    def test_relancer_ne_cree_pas_de_doublon(self):
        index_all()
        index_all()
        self.assertEqual(Skill.objects.count(), 6)

    def test_taille_du_departement(self):
        index_all()
        self.assertGreater(department_tokens("customer-service")["total"], 3000)

    def test_regles_de_validation(self):
        tools = read_tools()
        skill = {"department": "customer-service", "allowed_tools": ["get_order"],
                 "description": "Check orders. Use when asked.", "body": "Call get_order.", "body_tokens": 10}
        self.assertEqual(check_skill(skill, tools), ("active", []))
        self.assertEqual(check_skill({**skill, "allowed_tools": ["outil_imaginaire"]}, tools)[0], "rejected")
        self.assertEqual(check_skill({**skill, "department": "hr"}, tools)[0], "rejected")   # outil interdit
        self.assertEqual(check_skill({**skill, "description": "Check orders."}, tools)[0], "needs_review")

    def test_count_tokens(self):
        self.assertEqual(count_tokens(""), 0)
        self.assertGreater(count_tokens("Bonjour tout le monde"), 2)
