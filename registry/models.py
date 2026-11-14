from django.db import models


class AgentsFile(models.Model):
    """Un fichier AGENTS.md : global (niveau 1), département (2) ou sous-domaine (3)."""

    class Level(models.IntegerChoices):
        GLOBAL = 1, "Global"
        DEPARTMENT = 2, "Département"
        SUBDOMAIN = 3, "Sous-domaine"

    level = models.PositiveSmallIntegerField(choices=Level)
    department = models.CharField(max_length=64, blank=True)
    subdomain = models.CharField(max_length=64, blank=True)
    path = models.CharField(max_length=300, unique=True)  # relatif à la racine du dépôt
    content = models.TextField()
    tokens = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["level", "department", "subdomain"]

    def __str__(self):
        return f"AGENTS.md niveau {self.level} : {self.path}"


class Skill(models.Model):
    """Un skill décrit par un SKILL.md (index de niveau 1, corps de niveau 2)."""

    name = models.CharField(max_length=64, unique=True)
    description = models.TextField()
    allowed_tools = models.JSONField(default=list, blank=True)
    department = models.CharField(max_length=64)
    subdomain = models.CharField(max_length=64)
    path = models.CharField(max_length=300, unique=True)  # relatif à la racine du dépôt
    body = models.TextField()
    meta_tokens = models.PositiveIntegerField()
    body_tokens = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department", "subdomain", "name"]

    def __str__(self):
        return f"{self.department}/{self.subdomain}/{self.name}"