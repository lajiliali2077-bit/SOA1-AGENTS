from django.core.management.base import BaseCommand, CommandError

from registry.indexer import index_all, relative_path
from registry.validation import ACTIVE, ERROR, NEEDS_REVIEW, REJECTED, WARNING


class Command(BaseCommand):
    help = "Valide et indexe les skills, les outils et les AGENTS.md dans le registre (relançable)."

    def handle(self, *args, **options):
        report = index_all()

        if report.catalog_errors:
            for error in report.catalog_errors:
                self.stderr.write(self.style.ERROR(f"ERREUR CATALOGUE : {error}"))
            raise CommandError("Catalogue d'outils invalide : rien n'a été enregistré.")

        for r in report.needs_review:
            self.stdout.write(self.style.WARNING(f"À VALIDER : {relative_path(r.path)}"))
            for issue in r.issues:
                if issue.severity == WARNING:
                    self.stdout.write(self.style.WARNING(f"    {issue.code} : {issue.message}"))
        for r in report.rejected:
            self.stderr.write(self.style.ERROR(f"REJETÉ : {relative_path(r.path)}"))
            for issue in r.issues:
                if issue.severity == ERROR:
                    self.stderr.write(self.style.ERROR(f"    {issue.code} : {issue.message}"))

        for label, title in (("tools", "Outils"), ("skills", "Skills"), ("agents", "AGENTS.md")):
            self.stdout.write(self.style.SUCCESS(
                f"{title} : {report.created[label]} créés, {report.refreshed[label]} rafraîchis, "
                f"{report.removed[label]} supprimés."
            ))
        counts = report.status_counts
        self.stdout.write(
            f"Statuts des skills : {counts[ACTIVE]} active, {counts[NEEDS_REVIEW]} needs_review, "
            f"{counts[REJECTED]} rejected."
        )
        if report.rejected:
            raise CommandError(f"{len(report.rejected)} skill(s) rejeté(s) : indexation partielle, corrigez-les.")