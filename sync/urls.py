from django.urls import path

from . import views

urlpatterns = [
    path("api/sync/github/", views.github_webhook, name="sync-github"),
    path("api/sync/n8n/", views.n8n_trigger, name="sync-n8n"),
    path("api/sync/events/", views.events, name="sync-events"),
]
