"""Tests du service Outils : les vraies fonctions sur la base de démonstration."""

from django.test import TestCase

from engine.executor import execute_tool

from .models import Refund
from .seed import seed_demo
from .tools import ToolError, calculate, create_refund, get_customer, get_order, track_shipment


class ToolTests(TestCase):
    def setUp(self):
        seed_demo()

    def test_lecture(self):
        order = get_order("CMD-2026-0457")
        self.assertEqual(order["total_tnd"], 349.0)
        self.assertEqual(order["days_since_delivery"], 4)
        self.assertEqual(order["lines"][0]["category"], "electronics")
        self.assertEqual(track_shipment("CMD-2026-0601")["days_late"], 5)
        self.assertEqual(len(get_order("CMD-2026-0733")["lines"]), 350)

    def test_donnees_personnelles_masquees(self):
        customer = get_customer("C-1001")
        self.assertEqual(customer["email"], "s****@example.com")
        self.assertEqual(customer["phone"], "****3456")

    def test_ecriture_et_limite(self):
        result = create_refund("CMD-2026-0512", 119, "taille trop petite", "A-03")
        self.assertTrue(result["saved"])
        self.assertEqual(Refund.objects.filter(order__order_id="CMD-2026-0512").count(), 1)
        with self.assertRaises(ToolError):          # jamais plus que le total payé
            create_refund("CMD-2026-0512", 1, "encore", "A-03")

    def test_calculatrice_sans_eval(self):
        self.assertEqual(calculate("2 * 39.5 + 40")["result"], 119)
        with self.assertRaises(ToolError):
            calculate("__import__('os')")

    def test_executeur(self):
        self.assertIn("CMD-2026-0457", execute_tool("get_order", {"order_id": "CMD-2026-0457"}))
        self.assertIn("introuvable", execute_tool("get_order", {"order_id": "X"}))
        self.assertIn("implémentation", execute_tool("outil_imaginaire", {}))
