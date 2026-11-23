"""Tests du compilateur de contexte (avec les vrais fichiers du dépôt)."""

from django.test import TestCase

from registry.loader import index_all

from .core import Event, compile_context

USER = Event(kind="user", text="La cliente demande le remboursement de CMD-2026-0457.")
RETURN = Event(kind="activate_skill", skill="return-request")
TRACKING = Event(kind="activate_skill", skill="order-tracking")
SUMMARY = Event(kind="activate_skill", skill="customer-summary")
POLICY = Event(kind="load_reference", skill="return-request", filename="refund_policy.md")


def observation(n, lines=200):
    return Event(kind="observation", tool="get_order", text="ligne\n" * lines, obs_id=f"obs-{n:04d}")


class CompilerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        index_all()

    def test_niveau_1_au_demarrage(self):
        result = compile_context([USER])
        self.assertIn("Skills disponibles", result.text)
        self.assertIn("return-request", result.text)        # dans l'index
        self.assertNotIn("## Procedure", result.text)         # mais pas son corps
        self.assertEqual(result.active_skills, [])
        self.assertEqual(result.allowed_tools, [])            # aucun outil avant un skill

    def test_niveau_2_activation(self):
        result = compile_context([USER, RETURN])
        self.assertEqual(result.active_skills, ["return-request"])
        self.assertIn("Skill activé : return-request", result.text)
        self.assertIn("create_refund", result.allowed_tools)
        self.assertIn('"name": "create_refund"', result.text)  # la définition est envoyée à l'IA
        # ordre : global, département, sous-domaine (la règle la plus proche est lue en dernier)
        paths = [b.source for b in result.blocks if b.kind == "agents"]
        self.assertEqual(paths, ["AGENTS.md", "departments/customer-service/AGENTS.md",
                                 "departments/customer-service/returns/AGENTS.md"])

    def test_niveau_3_reference(self):
        result = compile_context([USER, RETURN, POLICY])
        self.assertIn("Référence : return-request/refund_policy.md", result.text)
        with self.assertRaises(ValueError):       # skill non actif
            compile_context([USER, POLICY])
        with self.assertRaises(ValueError):       # sortie du dossier references/ interdite
            compile_context([RETURN, Event(kind="load_reference", skill="return-request", filename="../SKILL.md")])

    def test_deux_skills_maximum(self):
        result = compile_context([RETURN, TRACKING, SUMMARY])
        self.assertEqual(result.active_skills, ["order-tracking", "customer-summary"])
        self.assertEqual(result.evictions, ["deactivated:return-request"])

    def test_masquage_des_anciennes_observations(self):
        events = [USER, RETURN] + [observation(n) for n in range(1, 5)]
        result = compile_context(events, budget=compile_context(events, budget=10**6).tokens)
        self.assertEqual(result.evictions, ["masked:obs-0001", "masked:obs-0002"])
        self.assertIn("[sortie masquée : get_order, 200 lignes", result.text)

    def test_pas_de_masquage_sous_70_pour_cent(self):
        events = [USER, RETURN] + [observation(n) for n in range(1, 5)]
        self.assertFalse(compile_context(events, budget=10**6).compacted)

    def test_budget_reference_puis_skill(self):
        events = [USER, RETURN, POLICY, TRACKING]
        small = compile_context([USER, TRACKING]).tokens
        result = compile_context(events, budget=small)
        self.assertEqual(result.evictions, ["unloaded:return-request/refund_policy.md",
                                            "deactivated:return-request"])
        self.assertEqual(result.active_skills, ["order-tracking"])   # le plus récent reste

    def test_monolithique_charge_tout(self):
        progressive = compile_context([USER])
        monolithic = compile_context([USER], mode="monolithic")
        self.assertEqual(len(monolithic.active_skills), 6)
        self.assertEqual(len(monolithic.allowed_tools), 8)
        self.assertIn("Référence : return-request/refund_policy.md", monolithic.text)
        self.assertGreater(monolithic.tokens, 4 * progressive.tokens)
        self.assertFalse(compile_context([USER], budget=1, mode="monolithic").compacted)

    def test_meme_entree_meme_sortie(self):
        events = [USER, RETURN, POLICY]
        self.assertEqual(compile_context(events).text, compile_context(events).text)

    def test_erreurs(self):
        with self.assertRaises(ValueError):
            compile_context([Event(kind="activate_skill", skill="inconnu")])
        with self.assertRaises(ValueError):
            compile_context([], mode="autre")
