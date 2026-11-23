from django.db import models


class AgentsFile(models.Model):
    """Un fichier AGENTS.md : 1 = global, 2 = département, 3 = sous-domaine."""

    path = models.CharField(max_length=300, unique=True)
    level = models.IntegerField()
    department = models.CharField(max_length=64, blank=True)
    subdomain = models.CharField(max_length=64, blank=True)
    content = models.TextField()
    tokens = models.IntegerField()

    class Meta:
        ordering = ["level", "path"]

    def __str__(self):
        return self.path


class Skill(models.Model):
    """Un skill (fichier SKILL.md). Les skills rejetés ne sont jamais enregistrés."""

    name = models.CharField(max_length=64, unique=True)
    description = models.TextField()
    department = models.CharField(max_length=64)
    subdomain = models.CharField(max_length=64)
    path = models.CharField(max_length=300)            # chemin du SKILL.md
    body = models.TextField()                          # procédure (niveau 2)
    allowed_tools = models.JSONField(default=list)
    status = models.CharField(max_length=16)           # active | needs_review
    index_tokens = models.IntegerField()               # coût de la ligne d'index (niveau 1)
    body_tokens = models.IntegerField()                # coût du corps (niveau 2)

    class Meta:
        ordering = ["department", "name"]

    def __str__(self):
        return self.name


class Tool(models.Model):
    """Un outil décrit dans tools/<département>.yaml."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    mode = models.CharField(max_length=5)              # read | write
    owner = models.CharField(max_length=64)            # département propriétaire
    departments = models.JSONField(default=list)       # départements autorisés
    parameters = models.JSONField(default=list)
    tokens = models.IntegerField()

    class Meta:
        ordering = ["owner", "name"]

    def __str__(self):
        return self.name
