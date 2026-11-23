from django.urls import path

from . import views

urlpatterns = [
    # Service Agent
    path("api/tasks/", views.tasks),
    path("api/run/", views.run_view),
    path("api/runs/", views.runs),
    path("api/runs/<int:run_id>/", views.run_detail),
    # Service Compilateur et Registre
    path("api/compile/", views.compile_view),
    path("api/tokens/", views.tokens),
    path("api/skills/", views.skills),
    # Service Outils
    path("api/tools/", views.tools),
    path("api/tools/<str:name>/", views.tool_call),
    # Service Masquage
    path("api/observations/<str:obs_id>/", views.observation),
    # Page web
    path("", views.home),
    path("dashboard/", views.home),
]
