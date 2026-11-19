"""Tests du mode monolithique (incrément 9). Ils créent leurs propres données de test."""

from django.test import TestCase

from registry.models import AgentsFile, Skill, Tool

from .core import compile_context
from .types import Event


class MonolithicModeTests(TestCase):
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
            allowed_tools=["get_invoice"], department="finance", subdomain="accounts-payable",
            path="departments/finance/accounts-payable/skills/invoice-validation/SKILL.md",
            body="corps facture", meta_tokens=10, body_tokens=5)
        Skill.objects.create(
            name="cv-screening", description="Trie des CV",
            allowed_tools=[], department="hr", subdomain="recruitment",
            path="departments/hr/recruitment/skills/cv-screening/SKILL.md",
            body="corps cv", meta_tokens=10, body_tokens=5)
        # get_candidate n'est autorisé par aucun skill : le monolithique le charge quand même.
        for name, owner, tokens in [("get_invoice", "finance", 100),
                                    ("update_invoice_status", "finance", 50),
                                    ("get_candidate", "hr", 100)]:
            Tool.objects.create(name=name, description="outil de test", mode="read",
                                owner=owner, departments=[owner], parameters=[], tokens=tokens)

    def test_tout_est_charge(self):
        result = compile_context([], mode="monolithic")
        for expected in ["Règles générales", "Règles finance", "Règles comptes fournisseurs",
                         "corps facture", "corps cv"]:
            self.assertIn(expected, result.text)
        self.assertNotIn("Skills disponibles", result.text)  # pas d'index en monolithique
        self.assertEqual(result.active_skills, ["invoice-validation", "cv-screening"])
        self.assertEqual(result.allowed_tools,
                         ["get_invoice", "update_invoice_status", "get_candidate"])
        self.assertEqual(result.tool_tokens, 250)
        self.assertEqual(result.tokens, sum(i.tokens for i in result.items) + 250)
        self.assertEqual(result.prefix_tokens, result.tokens - result.tool_tokens)

    def test_ordre_et_tiers(self):
        result = compile_context([], mode="monolithic")
        self.assertEqual([i.kind for i in result.items],
                         ["agents", "agents", "agents", "skill_body", "skill_body"])
        self.assertEqual([i.tier for i in result.items], [1, 2, 2, 2, 2])

    def test_pas_d_eviction_et_budget_depasse(self):
        result = compile_context([], budget=1, mode="monolithic")
        self.assertGreater(result.tokens, result.budget)
        self.assertFalse(result.compacted)
        self.assertEqual(result.evictions, [])

    def test_activation_et_reference_ignorees(self):
        """Tout est déjà chargé : ces événements n'ajoutent rien et ne lisent aucun fichier."""
        base = compile_context([Event(kind="user", text="Valide")], mode="monolithic")
        with_events = compile_context([
            Event(kind="user", text="Valide"),
            Event(kind="activate_skill", skill="invoice-validation"),
            Event(kind="load_reference", skill="invoice-validation", filename="absent.md"),
        ], mode="monolithic")
        self.assertEqual(base.text, with_events.text)

    def test_conversation_append_only(self):
        events = [Event(kind="user", text="Valide cette facture"),
                  Event(kind="assistant", text="Je regarde"),
                  Event(kind="user", text="Merci")]
        previous = compile_context([], mode="monolithic").text
        for n in range(1, len(events) + 1):
            current = compile_context(events[:n], mode="monolithic").text
            self.assertTrue(current.startswith(previous), f"préfixe cassé au tour {n}")
            self.assertGreater(len(current), len(previous))
            previous = current

    def test_skill_inconnu(self):
        with self.assertRaises(ValueError):
            compile_context([Event(kind="activate_skill", skill="n-existe-pas")], mode="monolithic")

    def test_mode_inconnu(self):
        with self.assertRaises(ValueError):
            compile_context([], mode="n_importe_quoi")

    def test_plus_gros_que_progressif(self):
        monolithic = compile_context([], mode="monolithic")
        progressive = compile_context([])
        self.assertGreater(monolithic.tokens, progressive.tokens)

    def test_deterministe(self):
        events = [Event(kind="user", text="Bonjour")]
        self.assertEqual(compile_context(events, mode="monolithic").text,
                         compile_context(events, mode="monolithic").text)

    