"""python manage.py seed_demo : (re)crée les données de démonstration de la boutique TechShop."""

from django.core.management.base import BaseCommand

from erp.models import Customer, Order, Product
from erp.seed import seed_demo


class Command(BaseCommand):
    help = "Remplit les tables de la boutique avec les données de démonstration."

    def handle(self, *args, **options):
        seed_demo()
        self.stdout.write(self.style.SUCCESS(
            f"Données créées : {Customer.objects.count()} clients, {Product.objects.count()} produits, "
            f"{Order.objects.count()} commandes"))
