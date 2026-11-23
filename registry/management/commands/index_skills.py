"""python manage.py index_skills : lit AGENTS.md, SKILL.md et tools/*.yaml et les enregistre en base."""

from django.conf import settings
from django.core.management.base import BaseCommand

from registry.loader import department_tokens, index_all


class Command(BaseCommand):
    help = "Valide et enregistre les skills, les outils et les AGENTS.md."

    def handle(self, *args, **options):
        summary = index_all()

        for path, problems in summary["needs_review"].items():
            self.stdout.write(self.style.WARNING(f"À VALIDER : {path}"))
            for problem in problems:
                self.stdout.write(f"    {problem}")
        for path, problems in summary["rejected"].items():
            self.stdout.write(self.style.ERROR(f"REJETÉ : {path}"))
            for problem in problems:
                self.stdout.write(f"    {problem}")

        counts = summary["counts"]
        self.stdout.write(self.style.SUCCESS(
            f"Enregistré : {counts['skills']} skills, {counts['tools']} outils, "
            f"{counts['agents']} AGENTS.md"))
        self.stdout.write(f"Skills : {len(summary['active'])} active, "
                          f"{len(summary['needs_review'])} needs_review, "
                          f"{len(summary['rejected'])} rejected")

        self.stdout.write("Taille des départements (tokens) :")
        for folder in sorted((settings.BASE_DIR / "departments").iterdir()):
            if folder.is_dir():
                size = department_tokens(folder.name)
                self.stdout.write(f"    {folder.name} : {size['total']} "
                                  f"({size['markdown']} Markdown + {size['tools']} outils)")
