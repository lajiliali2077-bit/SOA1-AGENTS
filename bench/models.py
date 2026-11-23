from django.db import models


class Run(models.Model):
    """Une exécution de l'agent (une tâche ou un message libre) avec ses mesures de tokens."""

    task_id = models.CharField(max_length=32, blank=True)    # vide = message libre
    mode = models.CharField(max_length=16)                    # progressive | monolithic
    client = models.CharField(max_length=16)                  # gemini | scripted
    turns = models.JSONField(default=list)                    # détail de chaque étape
    checks = models.JSONField(default=list)                   # résultat des vérifications
    violations = models.JSONField(default=list)               # erreurs trouvées par le vérificateur
    answer = models.TextField(blank=True)                     # dernière réponse de l'agent
    llm_calls = models.IntegerField(default=0)                # nombre d'appels à l'IA
    total_tokens = models.IntegerField(default=0)             # somme des contextes envoyés
    peak_tokens = models.IntegerField(default=0)              # plus gros contexte envoyé
    passed = models.BooleanField(null=True)                   # None pour un message libre
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def to_dict(self) -> dict:
        return {"id": self.pk, "task_id": self.task_id, "mode": self.mode,
                "client": self.client, "answer": self.answer, "passed": self.passed,
                "checks": self.checks, "violations": self.violations,
                "llm_calls": self.llm_calls, "total_tokens": self.total_tokens,
                "peak_tokens": self.peak_tokens, "error": self.error, "turns": self.turns}
