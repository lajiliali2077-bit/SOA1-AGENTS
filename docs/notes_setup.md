New-Item -ItemType Directory -Force docs | Out-Null
@"
# Notes setup

## Incrément 1 : environnement
- Stack retenue : Python 3.14, Django 6.1.x, PostgreSQL (via Docker), tiktoken, API Gemini Flash/Flash-Lite, VS Code, GitHub Desktop.
- Choix : Django 6.1 supporte officiellement Python 3.12 à 3.14 et exige PostgreSQL 15 ou plus, donc PostgreSQL tournera dans Docker.
- Décision à défendre : tiktoken (tokenizer OpenAI) sert d'estimation hors ligne pour le budget de tokens. Le compte exact viendra du usage_metadata de Gemini dans le benchmark.

## Incrément 2 : dépôt et environnement virtuel
- Dépôt GitHub créé avec GitHub Desktop (.gitignore Python), environnement virtuel .venv, dépendances figées dans requirements.txt.
- Piège rencontré : python pointait vers 3.15, hors de la plage supportée par Django 6.1. L'installation de PyYAML a échoué (pas de wheel précompilée probable, build C++ demandé).
- Solution : le venv est créé avec py -3.14 pour imposer la version, sans toucher au PATH. À retenir : toujours vérifier python --version après activation du venv.
"@ | Set-Content docs/notes_setup.md -Encoding utf8
## Incrément 3 : PostgreSQL (Docker) et projet Django
- PostgreSQL 17 tourne dans Docker via docker-compose.yml (port 5433 côté hôte pour éviter un conflit avec un PostgreSQL local). Django 6.1 exige PostgreSQL 15 ou plus.
- Projet Django créé avec django-admin startproject config . (à la racine), settings.py lit la config base via variables d'environnement avec des défauts de dev.
- Piège rencontré : le fichier docker-compose.yml contenait des commandes PowerShell collées par erreur dans le fichier au lieu du terminal. Docker a signalé une erreur YAML à la ligne 2.
- Vérification : migrate réussi et tables visibles avec psql, donc Django écrit bien dans PostgreSQL et non dans SQLite.

## Incrément 4 : arborescence AGENTS.md et SKILL.md à 3 niveaux
- Architecture : niveau 1 global (AGENTS.md racine), niveau 2 département, niveau 3 sous-domaine. 4 départements (Finance, HR, Inventory, Compliance), 2 sous-domaines chacun, soit 8 sous-domaines et 12 skills, générés par scripts/generate_departments.ps1.
- Précédence : le compilateur assemblera les AGENTS.md dans l'ordre global, département, sous-domaine, et la règle la plus proche gagne, comme le dit la spécification AGENTS.md. Cet ordre général vers spécifique garde aussi un préfixe stable pour le KV-cache.
- Trois conflits volontaires pour tester la précédence et le benchmark : seuil d'approbation Finance (10000 TND) surchargé à 5000 en Accounts-Payable, seuil de réapprovisionnement Inventory (100) surchargé à 50 en Warehouse, période de revue Compliance (90 jours) surchargée à 180 en Audit.
- Écarts avec l'énoncé : la spécification SKILL.md n'a pas de champ trigger, le déclencheur est la phrase Use when dans la description. allowed-tools est expérimental et se présente comme une chaîne séparée par des espaces. Les skills Compliance sont tous en lecture seule, ce qui servira de cas de test pour les permissions d'outils.
- Application Django registry créée et enregistrée dans INSTALLED_APPS, prête pour le parser et les modèles.
