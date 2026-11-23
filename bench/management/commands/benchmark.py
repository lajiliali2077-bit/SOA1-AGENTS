"""python manage.py benchmark

Joue les 7 tâches en mode progressif puis en mode monolithique, avec les mêmes actions,
et compare les tokens envoyés au modèle. Résultat : docs/BENCHMARK.md et docs/benchmark.csv.
"""

import csv

from django.conf import settings
from django.core.management.base import BaseCommand

from bench.runner import run_task
from bench.tasks import load_tasks
from compiler.core import compile_context


class Command(BaseCommand):
    help = "Compare les tokens : mode progressif contre mode monolithique."

    def add_arguments(self, parser):
        parser.add_argument("--client", default="scripted", choices=["scripted", "gemini"])

    def handle(self, *args, **options):
        client = options["client"]
        rows = []
        for task in load_tasks():
            prog = run_task(task, client_kind=client, mode="progressive")
            mono = run_task(task, client_kind=client, mode="monolithic")
            saving = 100 * (mono.total_tokens - prog.total_tokens) / mono.total_tokens
            rows.append([task.id, task.trap, prog.llm_calls, prog.peak_tokens, mono.peak_tokens,
                         prog.total_tokens, mono.total_tokens, f"{saving:.1f} %",
                         "réussi" if prog.passed else "échec",
                         "réussi" if mono.passed else "échec"])
            self.stdout.write(f"{task.id} : {prog.total_tokens} contre {mono.total_tokens} tokens")

        header = ["tâche", "piège", "appels IA", "pic progressif", "pic monolithique",
                  "total progressif", "total monolithique", "économie",
                  "checks progressif", "checks monolithique"]
        total_prog = sum(r[5] for r in rows)
        total_mono = sum(r[6] for r in rows)
        start_prog = compile_context([]).tokens
        start_mono = compile_context([], mode="monolithic").tokens

        # Fichier CSV (pour Excel / les graphiques de la présentation)
        with open(settings.BASE_DIR / "docs" / "benchmark.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

        # Fichier Markdown (pour le rapport)
        lines = [
            "# Benchmark : mode progressif contre mode monolithique",
            "",
            f"Commande : `python manage.py benchmark --client {client}`. "
            f"Budget : {settings.TOKEN_BUDGET} tokens. Tokens comptés avec tiktoken (estimation).",
            "",
            "Avec le client `scripted`, les actions de l'agent sont écrites à l'avance "
            "(bench/scripted/finance.yaml) : les deux modes reçoivent exactement les mêmes actions.",
            "",
            f"Contexte au démarrage : {start_prog} tokens (progressif) contre {start_mono} tokens "
            f"(monolithique), soit {100 * (start_mono - start_prog) / start_mono:.1f} % de moins.",
            "",
            "| " + " | ".join(header) + " |",
            "|" + "---|" * len(header),
        ]
        for r in rows:
            lines.append("| " + " | ".join(str(x) for x in r) + " |")
        lines += [
            "",
            f"**Total : {total_prog} tokens (progressif) contre {total_mono} tokens (monolithique), "
            f"soit {100 * (total_mono - total_prog) / total_mono:.1f} % de moins.**",
            "",
            "Total = somme des contextes envoyés au modèle pendant la tâche. "
            "Pic = plus grand contexte envoyé en une fois.",
            "",
        ]
        (settings.BASE_DIR / "docs" / "BENCHMARK.md").write_text("\n".join(lines), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS("Écrit : docs/BENCHMARK.md et docs/benchmark.csv"))
