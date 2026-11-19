"""Tests incrément 10 : observations et désactivation du plus ancien skill."""

import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase

from registry.models import AgentsFile, Skill, Tool

from . import core
from .core import compile_context
from .types import Event

SKILL_DIR = "departments/finance/accounts-payable/skills/invoice-validation"


def activate(name):
    return Event(kind="activate_skill", skill=name)


def observation(obs_id="obs-0001", tool="get_invoice", text="Facture 42 : 1200 EUR"):
    return Event(kind="observation", tool=tool, text=text, obs_id=obs_id)


class ObservationsEtSkillsTests(TestCase):
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
        Skill.objects.create(
            name="cv-screening", description="Trie des CV",
            allowed_tools=[], department="hr", subdomain="recruitment",
            path="departments/hr/recruitment/skills/cv-screening/SKILL.md",
            body="corps cv", meta_tokens=10, body_tokens=5)
        for name, tokens in [("get_invoice", 10), ("approve_invoice", 12), ("get_vendor", 8)]:
            Tool.objects.create(name=name, description="outil de test", mode="read",
                                owner="finance", departments=["finance"], parameters=[],
                                tokens=tokens)

        # Faux dépôt dans un dossier temporaire, supprimé à la fin de chaque test.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        references = Path(tmp.name) / SKILL_DIR / "references"
        references.mkdir(parents=True)
        (references / "approval_matrix.md").write_text("Seuil 5000", encoding="utf-8")
        patcher = mock.patch.object(core, "REPO_ROOT", Path(tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    # ----- Observations -----

    def test_observation_ajoutee_a_la_fin(self):
        events = [Event(kind="user", text="Valide"), activate("invoice-validation"), observation()]
        result = compile_context(events)
        last = result.items[-1]
        self.assertEqual((last.tier, last.kind, last.source), (0, "observation", "obs-0001"))
        self.assertEqual(last.text, "Observation (get_invoice, obs-0001) :\nFacture 42 : 1200 EUR")
        self.assertGreater(last.tokens, 0)
        self.assertEqual(result.tokens, sum(i.tokens for i in result.items) + result.tool_tokens)
        self.assertFalse(result.compacted)

    def test_observation_append_only(self):
        events = [
            Event(kind="user", text="Valide cette facture"),
            activate("invoice-validation"),
            Event(kind="assistant", text="Je consulte la facture"),
            observation("obs-0001"),
            Event(kind="assistant", text="Facture lue"),
            observation("obs-0002", text="Fournisseur OK"),
        ]
        previous = compile_context([]).text
        for n in range(1, len(events) + 1):
            current = compile_context(events[:n]).text
            self.assertTrue(current.startswith(previous), f"préfixe cassé au tour {n}")
            previous = current

    def test_observation_sans_identifiant(self):
        with self.assertRaises(ValueError):
            compile_context([Event(kind="observation", tool="get_invoice", text="sortie")])

    def test_observation_sans_outil(self):
        with self.assertRaises(ValueError):
            compile_context([Event(kind="observation", text="sortie", obs_id="obs-0001")])

    def test_observation_en_double(self):
        with self.assertRaises(ValueError):
            compile_context([observation("obs-0001"), observation("obs-0001")])

    def test_observation_en_monolithique(self):
        result = compile_context([observation()], mode="monolithic")
        self.assertEqual(result.items[-1].kind, "observation")
        self.assertIn("Facture 42", result.text)

    # ----- Désactivation du plus ancien skill -----

    def test_sans_depassement_pas_de_desactivation(self):
        result = compile_context([activate("invoice-validation"), activate("vendor-check")])
        self.assertFalse(result.compacted)
        self.assertEqual(result.evictions, [])

    def test_troisieme_skill_desactive_le_plus_ancien(self):
        result = compile_context([activate("invoice-validation"), activate("vendor-check"),
                                  activate("cv-screening")])
        self.assertEqual(result.active_skills, ["vendor-check", "cv-screening"])
        self.assertNotIn("corps du skill", result.text)       # corps du plus ancien retiré
        self.assertIn("corps vendor", result.text)
        self.assertIn("corps cv", result.text)
        self.assertIn("Règles finance", result.text)           # AGENTS.md conservés
        self.assertTrue(result.compacted)
        self.assertEqual(result.evictions, ["deactivated:invoice-validation"])
        self.assertEqual(result.allowed_tools, ["get_vendor", "get_invoice"])
        self.assertEqual(result.tool_tokens, 18)
        self.assertEqual(result.tokens, sum(i.tokens for i in result.items) + 18)

    def test_troisieme_skill_retire_les_references_du_plus_ancien(self):
        events = [activate("invoice-validation"),
                  Event(kind="load_reference", skill="invoice-validation",
                        filename="approval_matrix.md"),
                  activate("vendor-check"), activate("cv-screening")]
        result = compile_context(events)
        self.assertNotIn("Seuil 5000", result.text)
        self.assertEqual([i for i in result.items if i.kind == "reference"], [])

    def test_reactivation_apres_desactivation(self):
        events = [activate("invoice-validation"), activate("vendor-check"),
                  activate("cv-screening"), activate("invoice-validation")]
        result = compile_context(events)
        self.assertEqual(result.active_skills, ["cv-screening", "invoice-validation"])
        self.assertEqual(result.evictions,
                         ["deactivated:invoice-validation", "deactivated:vendor-check"])
        self.assertEqual(result.text.count("corps du skill"), 1)
        self.assertEqual(result.text.count("Règles finance"), 1)   # jamais répété
        self.assertNotIn("corps vendor", result.text)