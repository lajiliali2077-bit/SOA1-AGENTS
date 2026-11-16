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

## Incrément 5 : parser SKILL.md
- Module registry/parser.py : sépare le frontmatter du corps, valide avec un modèle Pydantic v2 les champs de la spécification Agent Skills (name, description, allowed-tools, plus les champs optionnels), et refuse tout champ inconnu.
- Règles vérifiées dans la spécification : name en minuscules, chiffres et tirets (sans tiret au début, à la fin ni doublé), identique au nom du dossier ; description de 1 à 1024 caractères ; allowed-tools est une chaîne séparée par des espaces, que le parser transforme en liste.
- Règle propre au projet : une description sans Use when donne un avertissement, car la spécification dit seulement qu'elle devrait décrire quand utiliser le skill.
- Mesure avec tiktoken (estimation, pas le tokenizer de Gemini) : 12 skills valides, index de niveau 1 de 366 tokens, corps de niveau 2 de 452 tokens au total. L'écart est faible parce que nos corps sont très courts.
- Point à trancher avant le benchmark : enrichir le corpus (corps plus longs, fichiers references/ pour le niveau 3, définitions d'outils), sinon la progressive disclosure montrera peu de gain.
- 11 tests unitaires (cas valides et invalides, fins de ligne Windows, et validation des 12 skills réels) lancés avec python manage.py test registry.

## Incrément 6 : corpus enrichi, catalogue d'outils et gabarit Finance
- Constat : le corpus de départ était minuscule (index 366 tokens, corps 452), donc la progressive disclosure n'aurait montré aucun gain. Nous avons enrichi Finance (AGENTS.md aux 3 niveaux, corps de skills, fichiers references/ de niveau 3) et créé un catalogue de 12 outils dans tools/finance.yaml.
- Choix : les définitions d'outils sont séparées des skills, car la spécification SKILL.md ne connaît que les noms d'outils dans allowed-tools. Chaque outil porte un mode read ou write et la liste des départements autorisés, ce qui servira aux permissions.
- Mesure : Finance pèse 6554 tokens (4510 de Markdown et 2044 d'outils) et le corpus 8187 tokens. L'estimation initiale de 8000 à 10000 par département était trop haute, la cible révisée est d'environ 6500, soit environ 26500 pour 4 départements (extrapolation, à confirmer).
- Organisation : Finance sert de gabarit, HR, Inventory et Compliance seront enrichis par les autres membres avec docs/GUIDE_DEPARTEMENT.md. Scripts de mesure : measure_corpus.py et measure_dept.py.

## Incrément 7 : catalogue d'outils, permissions et validation avec statuts
- Catalogue d'outils tools/<département>.yaml chargé et validé par registry/tools.py (Pydantic) : mode read ou write, départements autorisés, paramètres typés. 21 outils au total (Finance 12, HR 4, Inventory 2 plus get_vendor partagé, Compliance 3). Les permissions sont dérivées du catalogue, pas d'un dictionnaire codé en dur.
- Validation registry/validation.py avec trois gravités : erreur (skill rejected : outil inconnu, outil hors du périmètre du département, nom en double, parsing), avertissement (needs_review : outil d'écriture, outil cité mais non déclaré, outil déclaré mais inutilisé, fichier references/ introuvable, description sans Use when) et info (tokens, references/ non citée).
- Choix : aucun département n'est en lecture seule. Chacun peut recevoir des outils d'écriture, qui donnent needs_review (validation humaine) sans refus. Cela corrige la remarque de l'incrément 4 qui parlait de skills Compliance en lecture seule : ce n'était qu'un état de départ.
- Résultat sur le corpus actuel : 12 skills, 10 active, 2 needs_review (invoice-validation pour son outil d'écriture, finding-report pour un outil déclaré mais jamais cité). Règles propres au projet, pas de la spécification SKILL.md.
- 29 tests unitaires environ (catalogue, validation, corpus réel) avec python manage.py test registry.

## Incrément 8 : registre en base de données (indexeur et commande index_skills)
- Trois modèles Django : AgentsFile (13 fichiers aux 3 niveaux), Skill (statut active ou needs_review, liste des problèmes en JSON, tokens d'index et de corps) et Tool (catalogue d'outils avec mode, propriétaire, départements autorisés et paramètres). Le registre est un index : la source de vérité reste departments/ et tools/.
- Indexeur registry/indexer.py et commande python manage.py index_skills : relançable sans doublon (clé : chemin relatif du fichier, nom pour les outils), une seule transaction par exécution.
- Choix de nuance : un catalogue d'outils invalide n'écrit rien en base, car les permissions en dépendent. Un skill rejeté est exclu du registre (et supprimé s'il y était), les autres sont indexés, et la commande se termine en échec pour que l'auteur voie son erreur. Un skill needs_review est indexé avec ses avertissements.
- Contrôle croisé : les sommes de tokens lues dans PostgreSQL (index 409, corps 1732, outils 3631, AGENTS.md 530, 595 et 912) correspondent à celles des scripts de mesure indépendants. L'écart initial de 10 tokens au niveau 2 venait d'un fichier Compliance modifié entre deux mesures.
- Tests : le parser, la validation et l'indexeur sont testés sur des arborescences temporaires (relance, fichier modifié ou supprimé, skill devenu invalide, catalogue cassé sans écriture), plus un test sur le vrai corpus qui accepte l'ajout de skills par l'équipe.
