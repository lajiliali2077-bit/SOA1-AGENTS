"""Les tables de la boutique sont visibles dans /admin/ (python manage.py createsuperuser)."""
from django.contrib import admin

from . import models

for model in (models.Customer, models.Product, models.Order, models.OrderLine,
              models.TrackingEvent, models.Refund):
    admin.site.register(model)
