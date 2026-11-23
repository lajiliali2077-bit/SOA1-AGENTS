"""python manage.py run_task fin-01 [--client scripted|gemini] [--mode progressive|monolithic]

Joue une tâche et affiche chaque étape, les tokens et le résultat des checks.
"""

from django.core.management.base import BaseCommand

from bench.runner import run_task
from bench.tasks import get_task


class Command(BaseCommand):
    help = "Joue une tâche du dossier tasks/ et affiche le détail."

    def add_arguments(self, parser):
        parser.add_argument("task_id")
        parser.add_argument("--client", default="auto", choices=["scripted", "gemini", "auto"])
        parser.add_argument("--mode", default="progressive", choices=["progressive", "monolithic"])

    def handle(self, *args, **options):
        task = get_task(options["task_id"])
        run = run_task(task, client_kind=options["client"], mode=options["mode"])

        self.stdout.write(f"=== {task.id} : {task.title} ({run.mode}, client {run.client})")
        for number, turn in enumerate(run.turns, start=1):
            self.stdout.write(f"--- tour {number}")
            for step in turn["steps"]:
                guard = f" [garde : {step['guard']}]" if step["guard"] else ""
                self.stdout.write(f"  {step['action']} {step['detail']}{guard} ({step['tokens']} tokens)")
            self.stdout.write("  Réponse :")
            self.stdout.write("    " + turn["answer"].strip().replace("\n", "\n    "))
            for v in turn["violations"]:
                self.stdout.write(f"  Violation : {v}")
            if turn["error"]:
                self.stdout.write(f"  Erreur : {turn['error']}")

        self.stdout.write("--- checks")
        for c in run.checks:
            self.stdout.write(f"  {'OK' if c['passed'] else 'ÉCHEC'} {c['check']} : {c['detail']}")
        self.stdout.write(f"Résultat : {'RÉUSSI' if run.passed else 'ÉCHEC'}, "
                          f"{run.llm_calls} appels à l'IA, {run.total_tokens} tokens au total")
