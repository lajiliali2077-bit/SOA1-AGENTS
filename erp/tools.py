"""Service Outils : les vraies fonctions que l'IA peut demander d'exécuter.

Chaque outil est une petite fonction Python qui lit ou modifie la base (erp/models.py)
et retourne un dictionnaire (transformé en JSON par engine/executor.py).
Leur description pour l'IA (nom, paramètres, read/write) est dans tools/*.yaml.

Règle de confidentialité appliquée ici : l'e-mail et le téléphone du client ne sont jamais renvoyés en clair.
"""

import ast
import operator
from decimal import Decimal

from django.utils import timezone

from .models import Customer, Order, Product, Refund


class ToolError(ValueError):
    """Erreur « normale » d'un outil (ex. commande introuvable) : elle est renvoyée à l'IA."""


def mask(value: str) -> str:
    """Téléphone : garde les 4 derniers chiffres (****3456). E-mail : s****@example.com."""
    if "@" in value:
        name, domain = value.split("@", 1)
        return f"{name[0]}****@{domain}"
    return "****" + value.replace(" ", "")[-4:]


def find_order(order_id: str) -> Order:
    order = Order.objects.filter(order_id=order_id).first()
    if order is None:
        raise ToolError(f"commande {order_id} introuvable")
    return order


def order_total(order: Order) -> Decimal:
    return sum((line.quantity * line.unit_price_tnd for line in order.lines.all()), Decimal(0))


# ----- Commandes et livraisons -----

def get_order(order_id: str, line: int = None) -> dict:
    """Une commande et ses lignes. Avec line : seulement cette ligne (réponse courte)."""
    order = find_order(order_id)
    lines = order.lines.all() if line is None else order.lines.filter(line_no=line)
    today = timezone.localdate()
    return {
        "order_id": order.order_id, "customer_id": order.customer.customer_id,
        "order_date": str(order.order_date), "status": order.status,
        "expected_delivery": str(order.expected_delivery),
        "delivered_on": str(order.delivered_on) if order.delivered_on else None,
        "days_since_delivery": (today - order.delivered_on).days if order.delivered_on else None,
        "total_tnd": float(order_total(order)), "line_count": order.lines.count(),
        "customer_note": order.customer_note,
        "lines": [{"line": l.line_no, "sku": l.product.sku, "product": l.product.name,
                   "category": l.product.category, "quantity": l.quantity,
                   "unit_price_tnd": float(l.unit_price_tnd)} for l in lines],
    }


def track_shipment(order_id: str) -> dict:
    order = find_order(order_id)
    late_days = (timezone.localdate() - order.expected_delivery).days
    return {
        "order_id": order_id, "carrier": order.carrier, "tracking_number": order.tracking_number,
        "status": order.status, "expected_delivery": str(order.expected_delivery),
        "days_late": late_days if order.status != "delivered" and late_days > 0 else 0,
        "events": [{"date": str(e.date), "location": e.location, "status": e.status}
                   for e in order.events.all()],
    }


def get_customer(customer_id: str) -> dict:
    customer = Customer.objects.filter(customer_id=customer_id).first()
    if customer is None:
        raise ToolError(f"client {customer_id} introuvable")
    return {"customer_id": customer.customer_id, "name": customer.name, "city": customer.city,
            "loyalty_tier": customer.loyalty_tier, "email": mask(customer.email),
            "phone": mask(customer.phone), "orders_count": customer.order_set.count(),
            "refunds_count": Refund.objects.filter(order__customer=customer).count()}


def search_orders(customer_id: str, status: str = None, limit: int = 20) -> dict:
    orders = Order.objects.filter(customer__customer_id=customer_id).order_by("-order_date")
    if status:
        orders = orders.filter(status=status)
    rows = [{"order_id": o.order_id, "order_date": str(o.order_date), "status": o.status,
             "total_tnd": float(order_total(o)), "refunded": o.refunds.exists()}
            for o in orders[:min(limit, 100)]]
    return {"count": len(rows), "orders": rows}


def get_product(sku: str) -> dict:
    product = Product.objects.filter(sku=sku).first()
    if product is None:
        raise ToolError(f"produit {sku} introuvable")
    return {"sku": product.sku, "name": product.name, "category": product.category,
            "warranty_months": product.warranty_months}


# ----- Retours et remboursements -----

def get_refunds(order_id: str) -> dict:
    order = find_order(order_id)
    rows = [{"amount_tnd": float(r.amount_tnd), "reason": r.reason, "approved_by": r.approved_by,
             "date": timezone.localtime(r.created_at).strftime("%Y-%m-%d")} for r in order.refunds.all()]
    return {"order_id": order_id, "count": len(rows),
            "total_refunded_tnd": round(sum(r["amount_tnd"] for r in rows), 3), "refunds": rows}


def create_refund(order_id: str, amount_tnd: float, reason: str, approved_by: str) -> dict:
    """OUTIL D'ÉCRITURE : enregistre un remboursement dans la base."""
    order = find_order(order_id)
    already = sum((r.amount_tnd for r in order.refunds.all()), Decimal(0))
    amount = Decimal(str(amount_tnd))
    if amount <= 0:
        raise ToolError("le montant doit être positif")
    if already + amount > order_total(order):
        raise ToolError(f"impossible : on ne rembourse jamais plus que le total payé "
                        f"({order_total(order)} TND, déjà remboursé {already} TND)")
    refund = Refund.objects.create(order=order, amount_tnd=amount, reason=reason, approved_by=approved_by)
    return {"refund_id": f"RMB-{refund.pk:05d}", "order_id": order_id,
            "amount_tnd": float(amount), "approved_by": approved_by, "saved": True}


# ----- Outil commun : calculatrice -----

OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
             ast.Div: operator.truediv, ast.USub: operator.neg}


def calculate(expression: str) -> dict:
    """Calcule une expression simple (+ - * / et parenthèses) sans utiliser eval()."""
    def value(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](value(node.left), value(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](value(node.operand))
        raise ToolError("seuls les nombres, + - * / et les parenthèses sont acceptés")
    try:
        result = value(ast.parse(expression, mode="eval").body)
    except (SyntaxError, ZeroDivisionError) as exc:
        raise ToolError(f"expression invalide : {exc}") from None
    return {"expression": expression, "result": round(result, 3)}


# Le catalogue : nom de l'outil (comme dans tools/*.yaml) -> fonction Python
TOOLS = {f.__name__: f for f in [
    get_order, track_shipment, get_customer, search_orders, get_product, get_refunds,
    create_refund, calculate,
]}
