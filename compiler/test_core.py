"""Tests du compilateur (version 2). Ils créent leurs propres données de test."""

from django.test import TestCase

from registry.models import AgentsFile, Skill, Tool

from .core import compile_context
from .types import Event


class CompileContextTests(TestCase):
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
            path="departments/finance/accounts-payable/skills/invoice-validation/SKILL.md",
            body="corps du skill", meta_tokens=10, body_tokens=5,
        )
        Skill.objects.create(
            name="vendor-check", description="Vérifie un fournisseur",
            allowed_tools=["get_vendor", "get_invoice"],
            department="finance", subdomain="accounts-payable",
            path="departments/finance/accounts-payable/skills/vendor-check/SKILL.md",
            body="corps vendor", meta_tokens=10, body_tokens=5,
        )
        # Skill d'un autre département, sans AGENTS.md en base.
        Skill.objects.create(
            name="cv-screening", description="Trie des CV",
            allowed_tools=[], department="hr", subdomain="recruitment",
            path="departments/hr/recruitment/skills/cv-screening/SKILL.md",
            body="corps cv", meta_tokens=10, body_tokens=5,
        )
        for name, tokens in [("get_invoice", 10), ("approve_invoice", 12), ("get_vendor", 8)]:
            Tool.objects.create(name=name, description="outil de test", mode="read",
                                owner="finance", departments=["finance"], parameters=[],
                                tokens=tokens)

    def test_tier1_sans_evenement(self):
        result = compile_context([])
        self.assertIn("Règles générales", result.text)
        self.assertIn("invoice-validation", result.text)
        self.assertGreater(result.prefix_tokens, 0)
        self.assertEqual(result.tokens, result.prefix_tokens)

    def test_le_tier1_vient_en_premier(self):
        tier1 = compile_context([]).text
        result = compile_context([Event(kind="user", text="Valide cette facture")])
        self.assertTrue(result.text.startswith(tier1))

    def test_append_only(self):
        """Le texte du tour N commence par celui du tour N-1."""
        events = [
            Event(kind="user", text="Valide cette facture"),
            Event(kind="assistant", text="Je regarde"),
            Event(kind="user", text="Merci"),
        ]
        previous = compile_context([]).text
        for n in range(1, len(events) + 1):
            current = compile_context(events[:n]).text
            self.assertTrue(current.startswith(previous), f"préfixe cassé au tour {n}")
            self.assertGreater(len(current), len(previous))
            previous = current

    def test_deterministe(self):
        events = [Event(kind="user", text="Bonjour")]
        self.assertEqual(compile_context(events).text, compile_context(events).text)

    def test_evenement_inconnu(self):
        with self.assertRaises(ValueError):
            compile_context([Event(kind="n_importe_quoi")])

    def test_evenement_pas_encore_implemente(self):
        with self.assertRaises(NotImplementedError):
            compile_context([Event(kind="load_reference", skill="invoice-validation",
                                   filename="approval_matrix.md")])

    def test_mode_monolithique_pas_encore_implemente(self):
        with self.assertRaises(NotImplementedError):
            compile_context([], mode="monolithic")

    # ----- Incrément 7 : activation d'un skill (Tier 2) -----

    def test_activation_ordre_des_blocs(self):
        """Département, puis sous-domaine, puis corps du skill, tous à la fin."""
        events = [Event(kind="user", text="Valide cette facture"),
                  Event(kind="activate_skill", skill="invoice-validation")]
        result = compile_context(events)
        text = result.text
        self.assertLess(text.index("Utilisateur : Valide cette facture"), text.index("Règles finance"))
        self.assertLess(text.index("Règles finance"), text.index("Règles comptes fournisseurs"))
        self.assertLess(text.index("Règles comptes fournisseurs"), text.index("corps du skill"))
        last_three = result.items[-3:]
        self.assertEqual([i.kind for i in last_three], ["agents", "agents", "skill_body"])
        self.assertTrue(all(i.tier == 2 for i in last_three))
        self.assertEqual(result.active_skills, ["invoice-validation"])
        self.assertFalse(result.compacted)

    def test_activation_append_only(self):
        """Avec des activations au milieu de la conversation, le préfixe reste stable."""
        events = [
            Event(kind="user", text="Valide cette facture"),
            Event(kind="activate_skill", skill="invoice-validation"),
            Event(kind="assistant", text="Je regarde"),
            Event(kind="activate_skill", skill="vendor-check"),
            Event(kind="user", text="Merci"),
        ]
        previous = compile_context([]).text
        for n in range(1, len(events) + 1):
            current = compile_context(events[:n]).text
            self.assertTrue(current.startswith(previous), f"préfixe cassé au tour {n}")
            previous = current

    def test_agents_du_departement_pas_duplique(self):
        """Deux skills du même sous-domaine : les AGENTS.md ne sont ajoutés qu'une fois."""
        events = [Event(kind="activate_skill", skill="invoice-validation"),
                  Event(kind="activate_skill", skill="vendor-check")]
        result = compile_context(events)
        self.assertEqual(result.text.count("Règles finance"), 1)
        self.assertEqual(result.text.count("Règles comptes fournisseurs"), 1)
        self.assertEqual(result.active_skills, ["invoice-validation", "vendor-check"])

    def test_reactivation_sans_effet(self):
        once = compile_context([Event(kind="activate_skill", skill="invoice-validation")])
        twice = compile_context([Event(kind="activate_skill", skill="invoice-validation"),
                                 Event(kind="activate_skill", skill="invoice-validation")])
        self.assertEqual(once.text, twice.text)
        self.assertEqual(twice.active_skills, ["invoice-validation"])

    def test_skill_inconnu(self):
        with self.assertRaises(ValueError):
            compile_context([Event(kind="activate_skill", skill="n-existe-pas")])

    def test_troisieme_skill_pas_encore_implemente(self):
        events = [Event(kind="activate_skill", skill="invoice-validation"),
                  Event(kind="activate_skill", skill="vendor-check"),
                  Event(kind="activate_skill", skill="cv-screening")]
        with self.assertRaises(NotImplementedError):
            compile_context(events)

    def test_outils_autorises_et_tokens(self):
        events = [Event(kind="activate_skill", skill="invoice-validation"),
                  Event(kind="activate_skill", skill="vendor-check")]
        result = compile_context(events)
        self.assertEqual(result.allowed_tools, ["get_invoice", "approve_invoice", "get_vendor"])
        self.assertEqual(result.tool_tokens, 10 + 12 + 8)
        self.assertEqual(result.tokens, sum(i.tokens for i in result.items) + result.tool_tokens)

    def test_skill_sans_agents_en_base(self):
        """cv-screening n'a pas d'AGENTS.md en base : seul le corps est ajouté, sans erreur."""
        result = compile_context([Event(kind="activate_skill", skill="cv-screening")])
        self.assertEqual([i.kind for i in result.items[-1:]], ["skill_body"])
        self.assertNotIn("Règles finance", result.text)
        self.assertEqual(result.active_skills, ["cv-screening"])

    def test_activation_deterministe(self):
        events = [Event(kind="user", text="Bonjour"),
                  Event(kind="activate_skill", skill="invoice-validation")]
        self.assertEqual(compile_context(events).text, compile_context(events).text)