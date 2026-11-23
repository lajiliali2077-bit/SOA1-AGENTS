from django.db import models


class Observation(models.Model):
    """Sortie complète d'un outil, gardée pour pouvoir la relire après masquage."""

    tool = models.CharField(max_length=100)
    output = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def obs_id(self) -> str:
        return f"obs-{self.pk:04d}"

    def __str__(self):
        return self.obs_id
