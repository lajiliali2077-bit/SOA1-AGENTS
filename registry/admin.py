from django.contrib import admin

from .models import AgentsFile, Skill, Tool

admin.site.register([AgentsFile, Skill, Tool])
