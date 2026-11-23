"""python manage.py run_task cs-01 [--mode progressive|monolithic]

Fait exécuter une requête prédéfinie par Gemini et affiche chaque étape et les tokens.
"""

from django.core.management.base import BaseCommand, CommandError

from bench.llm import LLMError
from bench.runner import run_task
from bench.tasks import get_task


class Command(BaseCommand):
    help = "Fait exécuter une requête du dossier tasks/ par Gemini et affiche le détail."

    def add_arguments(self, parser):
        parser.add_argument("task_id")
        parser.add_argument("--mode", default="progressive", choices=["progressive", "monolithic"])

    def handle(self, *args, **options):
        try:
            run = run_task(get_task(options["task_id"]), mode=options["mode"])
        except (ValueError, LLMError) as exc:
            raise CommandError(str(exc))
        show(self.stdout, run)


def show(out, run):
    out.write(f"=== {run.task_id} : {run.title} ({run.mode}, {run.model})")
    for number, turn in enumerate(run.turns, start=1):
        out.write(f"--- tour {number} : {turn['user']}")
        for step in turn["steps"]:
            guard = f" [garde : {step['guard']}]" if step["guard"] else ""
            out.write(f"  {step['action']} {step['detail']}{guard}  "
                      f"(progressif {step['prog_tokens']} / monolithique {step['mono_tokens']} tokens)")
        out.write("  Réponse :\n    " + turn["answer"].strip().replace("\n", "\n    "))
        for v in turn["violations"]:
            out.write(f"  Violation : {v}")
        if turn["error"]:
            out.write(f"  Erreur : {turn['error']}")
    out.write("--- vérifications")
    for c in run.checks:
        out.write(f"  {'OK   ' if c['passed'] else 'ÉCHEC'} {c['check']} : {c['detail']}")
    out.write(f"Résultat : {'RÉUSSI' if run.passed else 'ÉCHEC'} | {run.llm_calls} appels à Gemini | "
              f"progressif {run.prog_tokens} contre monolithique {run.mono_tokens} tokens "
              f"({run.saving_pct} % d'économie) | facturés : {run.input_tokens} entrée + "
              f"{run.output_tokens} sortie | {run.duration_s} s")
