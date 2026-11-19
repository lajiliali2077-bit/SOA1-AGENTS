"""Tests de la conversion JSON (compiler/serialize.py)."""

import json

from django.test import TestCase

from registry.models import AgentsFile, Skill

from .core import compile_context
from .serialize import event_from_dict, events_from_list, result_to_dict
from .types import Event


class SerializeTests(TestCase):
    def setUp(self):
        AgentsFile.objects.create(level=1, path="AGENTS.md", content="Règles générales", tokens=3)
        Skill.objects.create(
            name="invoice-validation", description="Valide une facture fournisseur",
            allowed_tools=[], department="finance", subdomain="accounts-payable",
            path="departments/finance/accounts-payable/skills/invoice-validation/SKILL.md",
            body="corps du skill", meta_tokens=10, body_tokens=5)

    def test_event_valide(self):
        event = event_from_dict({"kind": "activate_skill", "skill": "invoice-validation"})
        self.assertEqual(event, Event(kind="activate_skill", skill="invoice-validation"))

    def test_champ_inconnu(self):
        with self.assertRaises(ValueError):
            event_from_dict({"kind": "user", "texte": "faute de frappe"})

    def test_kind_manquant(self):
        with self.assertRaises(ValueError):
            event_from_dict({"text": "bonjour"})

    def test_valeur_non_texte(self):
        with self.assertRaises(ValueError):
            event_from_dict({"kind": "user", "text": 42})

    def test_liste_invalide(self):
        with self.assertRaises(ValueError):
            events_from_list({"kind": "user"})
        with self.assertRaises(ValueError):
            events_from_list(["pas un objet"])

    def test_resultat_en_json(self):
        data = [{"kind": "user", "text": "Valide cette facture"},
                {"kind": "activate_skill", "skill": "invoice-validation"}]
        result = compile_context(events_from_list(data))
        as_dict = json.loads(json.dumps(result_to_dict(result)))  # doit passer par du vrai JSON
        self.assertEqual(as_dict["text"], result.text)
        self.assertEqual(as_dict["active_skills"], ["invoice-validation"])
        self.assertEqual(as_dict["items"][-1]["kind"], "skill_body")
        self.assertEqual(as_dict["tokens"], result.tokens)
        # Le même événement donne le même contexte, qu'il vienne du JSON ou du code.
        direct = compile_context([Event(kind="user", text="Valide cette facture"),
                                  Event(kind="activate_skill", skill="invoice-validation")])
        self.assertEqual(direct.text, result.text)