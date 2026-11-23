from django.urls import path

from . import views

urlpatterns = [
    path("api/tokens/", views.tokens),
    path("api/skills/", views.skills),
    path("api/compile/", views.compile_view),
    path("api/run/", views.run_view),
    path("api/runs/", views.runs),
    path("api/observations/<str:obs_id>/", views.observation),
    path("dashboard/", views.dashboard),
    path("", views.dashboard),
]
