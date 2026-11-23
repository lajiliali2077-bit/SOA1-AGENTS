"""Mini-ERP de démonstration : les vraies données de la boutique en ligne « TechShop ».

Les outils de l'agent (erp/tools.py) lisent et modifient ces tables.
Les données sont créées par `python manage.py seed_demo` (fichier erp/seed.py).
"""

from django.db import models

MONEY = {"max_digits": 10, "decimal_places": 3}


class Customer(models.Model):
    customer_id = models.CharField(max_length=10, unique=True)      # C-1001
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)                         # jamais montré en clair
    phone = models.CharField(max_length=30)                          # jamais montré en clair
    city = models.CharField(max_length=50)
    loyalty_tier = models.CharField(max_length=10)                   # standard | gold

    def __str__(self):
        return self.customer_id


class Product(models.Model):
    sku = models.CharField(max_length=12, unique=True)               # SKU-HP-01
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20)                       # electronics | accessories | clothing
    warranty_months = models.IntegerField(default=0)                 # garantie du fabricant

    def __str__(self):
        return self.sku


class Order(models.Model):
    order_id = models.CharField(max_length=16, unique=True)          # CMD-2026-0457
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order_date = models.DateField()
    status = models.CharField(max_length=12)                         # processing | shipped | delivered
    carrier = models.CharField(max_length=30)                        # transporteur
    tracking_number = models.CharField(max_length=20)
    expected_delivery = models.DateField()
    delivered_on = models.DateField(null=True, blank=True)
    customer_note = models.TextField(blank=True)                     # message libre écrit par le client

    def __str__(self):
        return self.order_id


class OrderLine(models.Model):
    order = models.ForeignKey(Order, related_name="lines", on_delete=models.CASCADE)
    line_no = models.IntegerField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price_tnd = models.DecimalField(**MONEY)

    class Meta:
        ordering = ["line_no"]


class TrackingEvent(models.Model):
    """Une étape du colis chez le transporteur."""
    order = models.ForeignKey(Order, related_name="events", on_delete=models.CASCADE)
    date = models.DateField()
    location = models.CharField(max_length=50)
    status = models.CharField(max_length=50)

    class Meta:
        ordering = ["date", "id"]


class Refund(models.Model):
    """Un remboursement. Créé uniquement par l'outil d'écriture create_refund."""
    order = models.ForeignKey(Order, related_name="refunds", on_delete=models.CASCADE)
    amount_tnd = models.DecimalField(**MONEY)
    reason = models.TextField()
    approved_by = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
