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
    """Un skill décrit par un SKILL.md (index de niveau 1, corps de niveau 2).

    Seuls les skills actifs ou à valider sont stockés : un skill rejeté par la validation
    n'entre jamais dans le registre.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Actif"
        NEEDS_REVIEW = "needs_review", "À valider"

    name = models.CharField(max_length=64)
    description = models.TextField()
    allowed_tools = models.JSONField(default=list, blank=True)
    department = models.CharField(max_length=64)
    subdomain = models.CharField(max_length=64)
    path = models.CharField(max_length=300, unique=True)  # relatif à la racine du dépôt
    body = models.TextField()
    meta_tokens = models.PositiveIntegerField()
    body_tokens = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status, default=Status.ACTIVE)
    issues = models.JSONField(default=list, blank=True)  # [{"severity", "code", "message"}]
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department", "subdomain", "name"]

    def __str__(self):
        return f"{self.department}/{self.subdomain}/{self.name}"


class Tool(models.Model):
    """Un outil du catalogue tools/<département>.yaml."""

    class Mode(models.TextChoices):
        READ = "read", "Lecture"
        WRITE = "write", "Écriture"

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    mode = models.CharField(max_length=5, choices=Mode)
    owner = models.CharField(max_length=64)  # département propriétaire (fichier tools/<owner>.yaml)
    departments = models.JSONField(default=list)  # départements autorisés à l'utiliser
    parameters = models.JSONField(default=list, blank=True)
    tokens = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["owner", "name"]

    def __str__(self):
        return f"{self.name} ({self.mode})"