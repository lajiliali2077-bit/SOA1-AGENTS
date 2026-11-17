"""Tests de l'éviction (incrément 10). Ils créent leurs propres données de test.

Pour fixer un budget sans deviner des nombres de tokens, on le calcule à partir d'une
autre compilation : par exemple « le budget = la taille du contexte sans la référence ».
"""

import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase

from registry.models import AgentsFile, Skill, Tool

from . import core
from .core import compile_context
from .types import Event

SKILL_DIR = "departments/finance/accounts-payable/skills/invoice-validation"
REF_MATRIX = f"{SKILL_DIR}/references/approval_matrix.md"
REF_OTHER = f"{SKILL_DIR}/references/other.md"

ACT_INVOICE = Event(kind="activate_skill", skill="invoice-validation")
ACT_VENDOR = Event(kind="activate_skill", skill="vendor-check")
ACT_CV = Event(kind="activate_skill", skill="cv-screening")
ACT_STOCK = Event(kind="activate_skill", skill="stock-check")
LOAD_MATRIX = Event(kind="load_reference", skill="invoice-validation", filename="approval_matrix.md")
LOAD_OTHER = Event(kind="load_reference", skill="invoice-validation", filename="other.md")
USER = Event(kind="user", text="Bonjour")


class EvictionTests(TestCase):
    def setUp(self):
        AgentsFile.objects.create(level=1, path="AGENTS.md", content="Règles générales", tokens=3)
        AgentsFile.objects.create(
            level=2, department="finance", path="departments/finance/AGENTS.md",
            content="Règles finance", tokens=3)
        AgentsFile.objects.create(
            level=3, department="finance", subdomain="accounts-payable",
            path="departments/finance/accounts-payable/AGENTS.md",
            content="Règles comptes fournisseurs", tokens=4)
        Skill.objects.create(
            name="invoice-validation", description="Valide une facture fournisseur",
            allowed_tools=["get_invoice", "approve_invoice"],
            department="finance", subdomain="accounts-payable",
            path=f"{SKILL_DIR}/SKILL.md", body="corps du skill", meta_tokens=10, body_tokens=5)
        Skill.objects.create(
            name="vendor-check", description="Vérifie un fournisseur",
            allowed_tools=["get_vendor", "get_invoice"],
            department="finance", subdomain="accounts-payable",
            path="departments/finance/accounts-payable/skills/vendor-check/SKILL.md",
            body="corps vendor", meta_tokens=10, body_tokens=5)
        # Deux skills d'autres départements, sans AGENTS.md en base.
        Skill.objects.create(
            name="cv-screening", description="Trie des CV",
            allowed_tools=[], department="hr", subdomain="recruitment",
            path="departments/hr/recruitment/skills/cv-screening/SKILL.md",
            body="corps cv", meta_tokens=10, body_tokens=5)
        Skill.objects.create(
            name="stock-check", description="Vérifie le stock",
            allowed_tools=[], department="inventory", subdomain="warehouse",
            path="departments/inventory/warehouse/skills/stock-check/SKILL.md",
            body="corps stock", meta_tokens=10, body_tokens=5)
        for name, tokens in [("get_invoice", 10), ("approve_invoice", 12), ("get_vendor", 8)]:
            Tool.objects.create(name=name, description="outil de test", mode="read",
                                owner="finance", departments=["finance"], parameters=[],
                                tokens=tokens)

        # Faux dépôt dans un dossier temporaire, supprimé à la fin de chaque test.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        references = Path(tmp.name) / SKILL_DIR / "references"
        references.mkdir(parents=True)
        (references / "approval_matrix.md").write_text("Seuil 500\nSeuil 5000", encoding="utf-8")
        (references / "other.md").write_text("Autre référence utile pour le test", encoding="utf-8")
        patcher = mock.patch.object(core, "REPO_ROOT", Path(tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    # ----- 3e skill actif : le plus ancien est désactivé (contrat, section 7) -----

    def test_troisieme_skill_desactive_le_plus_ancien(self):
        result = compile_context([ACT_INVOICE, ACT_VENDOR, ACT_CV])
        self.assertEqual(result.active_skills, ["vendor-check", "cv-screening"])
        self.assertEqual(result.evictions, ["deactivated:invoice-validation"])
        self.assertTrue(result.compacted)
        self.assertNotIn("corps du skill", result.text)
        self.assertIn("corps vendor", result.text)
        self.assertIn("corps cv", result.text)
        # vendor-check est du même sous-domaine : ses AGENTS.md restent, une seule fois.
        self.assertEqual(result.text.count("Règles finance"), 1)
        self.assertEqual(result.text.count("Règles comptes fournisseurs"), 1)
        # Les outils suivent les skills actifs.
        self.assertEqual(result.allowed_tools, ["get_vendor", "get_invoice"])
        self.assertEqual(result.tool_tokens, 8 + 10)
        self.assertEqual(result.tokens, sum(i.tokens for i in result.items) + result.tool_tokens)

    def test_agents_inutiles_retires_avec_le_skill(self):
        """Plus aucun skill de la finance : leurs AGENTS.md disparaissent aussi."""
        result = compile_context([ACT_INVOICE, ACT_CV, ACT_STOCK])
        self.assertEqual(result.active_skills, ["cv-screening", "stock-check"])
        self.assertNotIn("Règles finance", result.text)
        self.assertNotIn("Règles comptes fournisseurs", result.text)
        self.assertIn("Règles générales", result.text)  # Tier 1 intact

    def test_references_retirees_avec_leur_skill(self):
        events = [ACT_INVOICE, LOAD_MATRIX, ACT_VENDOR, ACT_CV]
        result = compile_context(events)
        self.assertNotIn("Seuil 5000", result.text)
        self.assertEqual(result.evictions, ["deactivated:invoice-validation"])
        # Le skill n'est plus actif : on ne peut plus charger ses références.
        with self.assertRaises(ValueError):
            compile_context(events + [LOAD_MATRIX])

    def test_reactivation_apres_desactivation(self):
        result = compile_context([ACT_INVOICE, ACT_VENDOR, ACT_CV, ACT_INVOICE])
        self.assertEqual(result.active_skills, ["cv-screening", "invoice-validation"])
        self.assertEqual(result.evictions,
                         ["deactivated:invoice-validation", "deactivated:vendor-check"])
        self.assertEqual(result.text.count("corps du skill"), 1)
        self.assertNotIn("corps vendor", result.text)

    # ----- Dépassement du budget : références d'abord, puis le skill le plus ancien -----

    def test_reference_dechargee_quand_le_budget_est_depasse(self):
        budget = compile_context([ACT_INVOICE, USER]).tokens
        self.assertGreater(compile_context([ACT_INVOICE, LOAD_MATRIX]).tokens, budget)  # précondition
        result = compile_context([ACT_INVOICE, LOAD_MATRIX, USER], budget=budget)
        self.assertEqual(result.evictions, [f"unloaded:{REF_MATRIX}"])
        self.assertTrue(result.compacted)
        self.assertNotIn("Seuil 5000", result.text)
        self.assertEqual(result.active_skills, ["invoice-validation"])  # le skill reste
        self.assertLessEqual(result.tokens, budget)

    def test_reference_protegee_pendant_son_propre_evenement(self):
        """La référence qu'on vient de charger n'est pas déchargée aussitôt."""
        budget = compile_context([ACT_INVOICE]).tokens
        result = compile_context([ACT_INVOICE, LOAD_MATRIX], budget=budget)
        self.assertIn("Seuil 5000", result.text)
        self.assertEqual(result.evictions, [])
        self.assertFalse(result.compacted)
        self.assertGreater(result.tokens, budget)  # budget dépassé, c'est assumé

    def test_reference_rechargeable_apres_eviction(self):
        budget = compile_context([ACT_INVOICE, USER]).tokens
        result = compile_context([ACT_INVOICE, LOAD_MATRIX, USER, LOAD_MATRIX], budget=budget)
        self.assertEqual(result.evictions, [f"unloaded:{REF_MATRIX}"])
        self.assertEqual(result.text.count("Seuil 5000"), 1)
        self.assertEqual(result.items[-1].kind, "reference")

    def test_la_plus_ancienne_reference_part_en_premier(self):
        budget = compile_context([ACT_INVOICE, LOAD_OTHER, USER]).tokens
        result = compile_context([ACT_INVOICE, LOAD_MATRIX, LOAD_OTHER, USER], budget=budget)
        self.assertEqual(result.evictions, [f"unloaded:{REF_MATRIX}"])
        self.assertNotIn("Seuil 5000", result.text)
        self.assertIn("Autre référence utile pour le test", result.text)

    def test_skill_le_plus_ancien_desactive_si_budget_depasse(self):
        budget = compile_context([ACT_VENDOR, USER]).tokens
        self.assertGreater(compile_context([ACT_INVOICE, ACT_VENDOR, USER]).tokens, budget)  # précondition
        result = compile_context([ACT_INVOICE, ACT_VENDOR, USER], budget=budget)
        self.assertEqual(result.evictions, ["deactivated:invoice-validation"])
        self.assertEqual(result.active_skills, ["vendor-check"])
        self.assertNotIn("corps du skill", result.text)
        self.assertLessEqual(result.tokens, budget)

    def test_le_dernier_skill_n_est_jamais_desactive(self):
        result = compile_context([ACT_INVOICE, USER], budget=1)
        self.assertEqual(result.active_skills, ["invoice-validation"])
        self.assertEqual(result.evictions, [])
        self.assertFalse(result.compacted)
        self.assertGreater(result.tokens, result.budget)

    def test_tier1_et_conversation_jamais_evinces(self):
        events = [Event(kind="user", text="Valide"), ACT_INVOICE, ACT_VENDOR,
                  Event(kind="assistant", text="Je regarde")]
        result = compile_context(events, budget=1)
        self.assertEqual(result.evictions, ["deactivated:invoice-validation"])
        for expected in ["Règles générales", "Skills disponibles",
                         "Utilisateur : Valide", "Assistant : Je regarde"]:
            self.assertIn(expected, result.text)

    # ----- Propriétés générales -----

    def test_sans_eviction_rien_ne_change(self):
        result = compile_context([USER, ACT_INVOICE, LOAD_MATRIX])
        self.assertFalse(result.compacted)
        self.assertEqual(result.evictions, [])

    def test_deterministe(self):
        events = [ACT_INVOICE, LOAD_MATRIX, USER, ACT_VENDOR, ACT_CV]
        first = compile_context(events, budget=30)
        second = compile_context(events, budget=30)
        self.assertEqual(first.text, second.text)
        self.assertEqual(first.evictions, second.evictions)

    def test_monolithique_jamais_evince(self):
        events = [ACT_INVOICE, ACT_VENDOR, ACT_CV, USER]
        result = compile_context(events, budget=1, mode="monolithic")
        self.assertFalse(result.compacted)
        self.assertEqual(result.evictions, [])