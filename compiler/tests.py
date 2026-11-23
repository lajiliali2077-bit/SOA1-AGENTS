"""Tests du compilateur de contexte (avec les vrais fichiers du dépôt)."""

from django.test import TestCase

from registry.loader import index_all

from .core import Event, compile_context

USER = Event(kind="user", text="Peux-tu approuver la facture INV-2026-00457 ?")
INVOICE = Event(kind="activate_skill", skill="invoice-validation")
VENDOR = Event(kind="activate_skill", skill="vendor-check")
FORECAST = Event(kind="activate_skill", skill="cash-forecast")
MATRIX = Event(kind="load_reference", skill="invoice-validation", filename="approval_matrix.md")


def observation(n, lines=200):
    return Event(kind="observation", tool="get_invoice", text="ligne\n" * lines, obs_id=f"obs-{n:04d}")


class CompilerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        index_all()

    def test_niveau_1_au_demarrage(self):
        result = compile_context([USER])
        self.assertIn("Skills disponibles", result.text)
        self.assertIn("invoice-validation", result.text)      # dans l'index
        self.assertNotIn("## Procedure", result.text)          # mais pas son corps
        self.assertEqual(result.active_skills, [])

    def test_niveau_2_activation(self):
        result = compile_context([USER, INVOICE])
        self.assertEqual(result.active_skills, ["invoice-validation"])
        self.assertIn("Skill activé : invoice-validation", result.text)
        self.assertIn("update_invoice_status", result.allowed_tools)
        # ordre : global, département, sous-domaine (la règle la plus proche est lue en dernier)
        paths = [b.source for b in result.blocks if b.kind == "agents"]
        self.assertEqual(paths, ["AGENTS.md", "departments/finance/AGENTS.md",
                                 "departments/finance/accounts-payable/AGENTS.md"])

    def test_niveau_3_reference(self):
        result = compile_context([USER, INVOICE, MATRIX])
        self.assertIn("Référence : invoice-validation/approval_matrix.md", result.text)
        with self.assertRaises(ValueError):       # skill non actif
            compile_context([USER, MATRIX])
        with self.assertRaises(ValueError):       # sortie du dossier references/ interdite
            compile_context([INVOICE, Event(kind="load_reference", skill="invoice-validation",
                                            filename="../SKILL.md")])

    def test_deux_skills_maximum(self):
        result = compile_context([INVOICE, VENDOR, FORECAST])
        self.assertEqual(result.active_skills, ["vendor-check", "cash-forecast"])
        self.assertEqual(result.evictions, ["deactivated:invoice-validation"])

    def test_masquage_des_anciennes_observations(self):
        events = [USER, INVOICE] + [observation(n) for n in range(1, 5)]
        result = compile_context(events, budget=compile_context(events, budget=10**6).tokens)
        self.assertEqual(result.evictions, ["masked:obs-0001", "masked:obs-0002"])
        self.assertIn("[sortie masquée : get_invoice, 200 lignes", result.text)
        self.assertTrue(result.compacted)

    def test_pas_de_masquage_sous_70_pour_cent(self):
        events = [USER, INVOICE] + [observation(n) for n in range(1, 5)]
        self.assertFalse(compile_context(events, budget=10**6).compacted)

    def test_budget_reference_puis_skill(self):
        events = [USER, INVOICE, MATRIX, VENDOR]
        small = compile_context([USER, VENDOR]).tokens
        result = compile_context(events, budget=small)
        self.assertEqual(result.evictions, ["unloaded:invoice-validation/approval_matrix.md",
                                            "deactivated:invoice-validation"])
        self.assertEqual(result.active_skills, ["vendor-check"])   # le plus récent reste

    def test_monolithique_charge_tout(self):
        progressive = compile_context([USER])
        monolithic = compile_context([USER, INVOICE], mode="monolithic")
        self.assertEqual(len(monolithic.active_skills), 12)
        self.assertEqual(len(monolithic.allowed_tools), 21)
        self.assertGreater(monolithic.tokens, 5 * progressive.tokens)
        self.assertFalse(compile_context([USER], budget=1, mode="monolithic").compacted)

    def test_meme_entree_meme_sortie(self):
        events = [USER, INVOICE, MATRIX]
        self.assertEqual(compile_context(events).text, compile_context(events).text)

    def test_erreurs(self):
        with self.assertRaises(ValueError):
            compile_context([Event(kind="activate_skill", skill="inconnu")])
        with self.assertRaises(ValueError):
            compile_context([], mode="autre")
