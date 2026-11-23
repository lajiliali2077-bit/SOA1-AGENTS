"""python manage.py demo [--client scripted|gemini|auto]

Démo de la soutenance : 3 scénarios courts, en mode progressif.
Par défaut, plan B hors ligne (client scripted) : aucune clé ni connexion Internet nécessaire.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand

SCENARIOS = [
    ("fin-01", "règle surchargée : seuil de 5000 TND du sous-domaine"),
    ("fin-02", "écriture refusée sans confirmation, acceptée après"),
    ("fin-07", "sortie d'outil énorme : masquage des observations"),
]


class Command(BaseCommand):
    help = "Joue les 3 scénarios de la démo."

    def add_arguments(self, parser):
        parser.add_argument("--client", default="scripted", choices=["scripted", "gemini", "auto"])

    def handle(self, *args, **options):
        if options["client"] == "scripted":
            self.stdout.write("PLAN B HORS LIGNE : actions rejouées depuis bench/scripted/finance.yaml\n")
        for task_id, idea in SCENARIOS:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n##### Scénario {task_id} : {idea}"))
            call_command("run_task", task_id, client=options["client"])
        self.stdout.write("\nComparaison des tokens : python manage.py benchmark, puis /dashboard/")
