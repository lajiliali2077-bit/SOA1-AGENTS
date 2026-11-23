"""Routes du projet : chaque service expose ses propres URL (architecture orientée services)."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('sync.urls')),
    path('', include('bench.urls')),
]
