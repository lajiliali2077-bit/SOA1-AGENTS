from django.db import models


class Run(models.Model):
    """Une exécution d'une requête prédéfinie, avec ses mesures de tokens."""

    task_id = models.CharField(max_length=32)
    title = models.CharField(max_length=200, blank=True)
    mode = models.CharField(max_length=16)                    # progressive | monolithic
    client = models.CharField(max_length=16)                  # gemini | scripted (tests)
    model = models.CharField(max_length=64, blank=True)       # gemini-3.5-flash-lite
    turns = models.JSONField(default=list)                    # détail de chaque étape
    checks = models.JSONField(default=list)                   # résultat des vérifications
    violations = models.JSONField(default=list)               # erreurs trouvées par le vérificateur
    answer = models.TextField(blank=True)                     # dernière réponse de l'agent
    llm_calls = models.IntegerField(default=0)                # nombre d'appels à Gemini
    prog_tokens = models.IntegerField(default=0)              # total des contextes avec notre compilateur
    mono_tokens = models.IntegerField(default=0)              # total du même historique en monolithique
    input_tokens = models.IntegerField(default=0)             # tokens réellement facturés en entrée
    output_tokens = models.IntegerField(default=0)            # ... en sortie
    thinking_tokens = models.IntegerField(default=0)          # ... de réflexion
    duration_s = models.FloatField(default=0)
    passed = models.BooleanField(null=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    @property
    def saving_pct(self):
        if not self.mono_tokens:
            return None
        return round(100 * (self.mono_tokens - self.prog_tokens) / self.mono_tokens, 1)

    def summary(self) -> dict:
        return {"id": self.pk, "task_id": self.task_id, "title": self.title, "mode": self.mode,
                "model": self.model, "passed": self.passed, "llm_calls": self.llm_calls,
                "prog_tokens": self.prog_tokens, "mono_tokens": self.mono_tokens,
                "saving_pct": self.saving_pct, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "thinking_tokens": self.thinking_tokens,
                "duration_s": self.duration_s, "error": self.error,
                "created_at": self.created_at.isoformat(timespec="seconds") if self.created_at else None}

    def to_dict(self) -> dict:
        return {**self.summary(), "answer": self.answer, "checks": self.checks,
                "violations": self.violations, "turns": self.turns}
