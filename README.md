# SOA1-AGENTS : copilote multi-départements (Context Engineering)

Projet 02 de la matière SOA (ISG Tunis, 3BI) : un harnais Django qui charge le contexte d'un agent **par couches** (AGENTS.md hiérarchiques et skills SKILL.md, progressive disclosure) au lieu de tout mettre dans un seul prompt.

## Prérequis
- Windows, PowerShell, Git (ou GitHub Desktop) et VS Code.
- **Python 3.14** (commande `py -3.14`). Django 6.1 supporte Python 3.12 à 3.14. Avec Python 3.15, l'installation de PyYAML échoue (elle réclame un compilateur C++).
- **Docker Desktop**, démarré : PostgreSQL 17 tourne dans un conteneur.

## Installation
```powershell
git clone https://github.com/lajiliali2077-bit/SOA1-AGENTS.git
cd SOA1-AGENTS
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
pip install -r requirements.txt
docker compose up -d
docker compose ps
python manage.py migrate
python manage.py index_skills
```
- `python --version` doit afficher `Python 3.14.x` (sinon, le venv n'utilise pas la bonne version).
- `docker compose ps` doit indiquer `healthy` avant de lancer `migrate`.
- Si PowerShell bloque l'activation du venv : `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.
- À la date de ce README, `index_skills` indexe 12 skills (10 `active`, 2 `needs_review`), 21 outils et 13 fichiers AGENTS.md.

## Commandes
| Commande | Rôle |
|---|---|
| `python scripts\validate_skills.py` (`--verbose` pour les infos) | valide les skills contre le catalogue d'outils, affiche le statut de chacun |
| `python scripts\check_tools.py` | valide `tools/*.yaml` et affiche les permissions par département |
| `python scripts\show_skills.py` | liste les skills avec leur coût en tokens |
| `python scripts\measure_corpus.py` | taille du corpus en tokens, par catégorie et par département |
| `python scripts\measure_dept.py <département>` | taille en tokens de chaque fichier d'un département |
| `python manage.py index_skills` | valide puis enregistre skills, outils et AGENTS.md dans PostgreSQL (relançable) |
| `python manage.py test registry --noinput` | lance les tests |

## Structure
```
AGENTS.md                                  niveau 1 : règles globales
departments/<dept>/AGENTS.md               niveau 2 : règles du département
departments/<dept>/<sous-domaine>/AGENTS.md          niveau 3 : règles du sous-domaine
departments/<dept>/<sous-domaine>/skills/<skill>/SKILL.md
departments/<dept>/<sous-domaine>/skills/<skill>/references/   niveau 3 des skills (à la demande)
tools/<dept>.yaml                          catalogue d'outils (mode read ou write, départements autorisés)
registry/                                  parser, validation, catalogue, indexeur, modèles, tests
scripts/                                   outils de vérification et de mesure
docs/                                      notes de travail et guide pour enrichir un département
```
Départements : `finance` (département de référence, enrichi), `hr`, `inventory`, `compliance`. Les AGENTS.md sont assemblés dans l'ordre global, département, sous-domaine : la règle la plus proche gagne.

## Travailler en équipe
Pour enrichir un département, lisez `docs/GUIDE_DEPARTEMENT.md` et prenez `departments/finance/` comme modèle.

1. **Jamais de push direct sur `main`.** Chacun travaille sur sa branche, créée à partir d'un `main` à jour.
2. **Avant de commencer :** mettre `main` à jour (Fetch puis Pull dans GitHub Desktop), puis fusionner `main` dans sa branche.
3. **Chacun son périmètre :** un membre modifie uniquement `departments/<son département>/` et `tools/<son département>.yaml`. Un outil partagé est défini une seule fois, dans le fichier de son département propriétaire.
4. **Fichiers partagés** (`AGENTS.md` racine, `registry/`, `config/`, `scripts/`, `docker-compose.yml`, `requirements.txt`) : modification seulement après accord de l'équipe, dans une Pull Request à part.
5. **Avant chaque commit :** lancer `validate_skills.py`, `check_tools.py` et les tests (voir Commandes). Aucun skill ne doit être `rejected`.
6. **Fusion :** Pull Request sur GitHub vers `main`, relue par un autre membre, avec l'option « Create a merge commit ».
7. **Ne jamais commiter** de clé d'API, de fichier `.env` ni le dossier `.venv`.

## Docker
- La base écoute sur le port **5433** de la machine (identifiants de développement dans `docker-compose.yml`).
- Arrêter la base : `docker compose stop`. La redémarrer : `docker compose up -d`.
- Effacer aussi les données : `docker compose down -v` (destructif).

## Dépannage
- `python manage.py makemigrations` ou `migrate` semble bloqué : la base est probablement arrêtée. Lancez `docker compose up -d` et attendez `healthy`.
- `python --version` affiche 3.15 dans le venv : supprimez `.venv` et recréez-le avec `py -3.14 -m venv .venv`.
- Texte accentué illisible dans PowerShell : les fichiers sont en UTF-8 sans BOM, ouvrez-les dans VS Code.

## Avancement
Registre (parser, validation, catalogue d'outils, indexeur) terminé. À venir : compilateur de contexte avec budget de tokens et observation masking, benchmark, webhooks GitHub/n8n, présentation. Répartition des rôles : à définir.