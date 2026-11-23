"""python manage.py check_gemini : un seul appel à Gemini pour vérifier la clé et le modèle."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bench.llm import GeminiClient, LLMError
from bench.schemas import StepError, parse_step


class Command(BaseCommand):
    help = "Teste la connexion à Gemini (un seul appel)."

    def handle(self, *args, **options):
        self.stdout.write(f"Modèle : {settings.GEMINI_MODEL}")
        try:
            client = GeminiClient()
            reply = client.next_step("Utilisateur : Bonjour, réponds simplement que tu es prêt.")
            counted = client.count_tokens("Bonjour tout le monde")
        except LLMError as exc:
            raise CommandError(str(exc))
        self.stdout.write(f"Réponse brute : {reply.text}")
        self.stdout.write(f"Tokens facturés : {reply.usage} ; consignes + « Bonjour tout le monde » = {counted} tokens")
        try:
            step = parse_step(reply.text)
        except StepError as exc:
            raise CommandError(f"Gemini a répondu, mais pas au bon format : {exc}")
        self.stdout.write(self.style.SUCCESS(f"Connexion OK. Action reçue : {step.action}"))
