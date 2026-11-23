"""python manage.py check_gemini

Vérifie que la connexion à Gemini fonctionne : un seul appel, puis affichage de la réponse.
À lancer après avoir mis GEMINI_API_KEY dans le fichier .env.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bench.llm import GeminiClient, LLMError
from bench.schemas import StepError, parse_step


class Command(BaseCommand):
    help = "Teste la connexion à Gemini Flash (un seul appel)."

    def handle(self, *args, **options):
        self.stdout.write(f"Modèle : {settings.GEMINI_MODEL}")
        try:
            client = GeminiClient()
            raw = client.next_step("Utilisateur : Bonjour, réponds simplement que tu es prêt.")
        except LLMError as exc:
            raise CommandError(f"{exc}\nPlan B : python manage.py demo (sans Internet)")
        self.stdout.write(f"Réponse brute : {raw}")
        try:
            step = parse_step(raw)
        except StepError as exc:
            raise CommandError(f"Gemini a répondu, mais pas au bon format : {exc}")
        self.stdout.write(self.style.SUCCESS(f"Connexion OK. Action reçue : {step.action}"))
