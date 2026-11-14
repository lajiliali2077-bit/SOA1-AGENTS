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