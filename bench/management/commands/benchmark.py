"""python manage.py benchmark [--real-monolithic]

Exécute toutes les requêtes prédéfinies avec Gemini en mode progressif. À chaque étape, le même
historique est aussi mesuré en mode monolithique (comptage réel par Gemini, sans génération).
Avec --real-monolithic, chaque requête est AUSSI exécutée pour de vrai en mode monolithique.
Résultat : docs/BENCHMARK.md et docs/benchmark.csv.
"""

import csv

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bench.llm import LLMError
from bench.models import Run
from bench.runner import run_task
from bench.tasks import load_tasks


class Command(BaseCommand):
    help = "Compare les tokens : avec notre compilateur (progressif) et sans (monolithique)."

    def add_arguments(self, parser):
        parser.add_argument("--real-monolithic", action="store_true")
        parser.add_argument("--only", default="", help="ex. cs-06,gen-01 : ne relance que ces requêtes")

    def handle(self, *args, **options):
        header = ["requête", "piège", "appels Gemini", "tokens progressif", "tokens monolithique",
                  "économie", "facturés entrée", "facturés sortie", "vérifications"]
        if options["real_monolithic"]:
            header += ["monolithique réel : facturés entrée", "monolithique réel : vérifications"]
        only = [t for t in options["only"].split(",") if t]
        rows = []
        for task in load_tasks():
            try:
                if only and task.id not in only:     # on reprend la dernière exécution enregistrée
                    run = Run.objects.filter(task_id=task.id, mode="progressive", client="gemini").first()
                    if run is None:
                        continue
                else:
                    run = run_task(task, mode="progressive")
                row = [task.id, task.trap, run.llm_calls, run.prog_tokens, run.mono_tokens,
                       f"{run.saving_pct} %", run.input_tokens, run.output_tokens,
                       "réussi" if run.passed else "échec"]
                if options["real_monolithic"]:
                    mono = run_task(task, mode="monolithic")
                    row += [mono.input_tokens, "réussi" if mono.passed else "échec"]
            except LLMError as exc:
                raise CommandError(str(exc))
            rows.append(row)
            self.stdout.write(f"{task.id} : {run.prog_tokens} contre {run.mono_tokens} tokens, "
                              f"{'réussi' if run.passed else 'échec'}")

        total_prog, total_mono = sum(r[3] for r in rows), sum(r[4] for r in rows)
        with open(settings.BASE_DIR / "docs" / "benchmark.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        lines = [
            "# Benchmark : avec notre compilateur (progressif) contre sans (monolithique)",
            "",
            f"Commande : `python manage.py benchmark`. Modèle : `{settings.GEMINI_MODEL}`. "
            f"Budget : {settings.TOKEN_BUDGET} tokens.",
            "",
            "Chaque requête est exécutée par Gemini en mode progressif. À chaque étape, le même "
            "historique est aussi construit en mode monolithique, et les deux contextes sont comptés "
            "par Gemini lui-même (API count_tokens). « Facturés » = tokens réellement consommés.",
            "",
            "| " + " | ".join(header) + " |",
            "|" + "---|" * len(header),
        ] + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows] + [
            "",
            f"**Total : {total_prog} tokens (progressif) contre {total_mono} tokens (monolithique), "
            f"soit {100 * (total_mono - total_prog) / total_mono:.1f} % de moins.**",
            "",
        ]
        (settings.BASE_DIR / "docs" / "BENCHMARK.md").write_text("\n".join(lines), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS("Écrit : docs/BENCHMARK.md et docs/benchmark.csv"))
