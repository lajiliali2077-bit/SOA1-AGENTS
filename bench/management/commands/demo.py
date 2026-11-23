"""python manage.py demo : les 3 scénarios de la soutenance, exécutés par Gemini."""

from django.core.management.base import BaseCommand, CommandError

from bench.llm import LLMError
from bench.runner import run_task
from bench.tasks import get_task

from .run_task import show

SCENARIOS = [
    ("cs-01", "règle surchargée : superviseur au-dessus de 200 TND (et non 300)"),
    ("cs-02", "écriture refusée sans confirmation, acceptée après"),
    ("cs-06", "sortie d'outil énorme (350 lignes) : masquage des observations"),
]


class Command(BaseCommand):
    help = "Joue les 3 scénarios de la démo avec Gemini."

    def handle(self, *args, **options):
        for task_id, idea in SCENARIOS:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n##### Scénario {task_id} : {idea}"))
            try:
                show(self.stdout, run_task(get_task(task_id)))
            except LLMError as exc:
                raise CommandError(str(exc))
        self.stdout.write("\nTableau de bord : python manage.py runserver, puis http://127.0.0.1:8000/")
