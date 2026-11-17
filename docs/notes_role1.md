## Incrément 1 : état des lieux du dépôt (17/11/2026)
- Vérifié : Python 3.14.10, Django 6.1.3, PostgreSQL 17 (Docker) fonctionnent ensemble ; 41 tests du registry OK.
- Les tests Django ont besoin du conteneur PostgreSQL démarré (docker compose up -d db) : sans lui, ils se bloquent en attendant la connexion.
- Choix : on n'a rien modifié (settings.py et docker-compose.yml appartiennent au Role 4).
- Constaté : pytest et pytest-django ne sont pas installés ; ce sera notre configuration pytest (D11 : les tests actuels doivent tourner tels quels).

## Incrément 2 : lecture du registre (17/11/2026)
- Lu : registry/models.py et indexer.py. Le registre stocke 3 tables : AgentsFile (niveaux 1/2/3), Skill (index + corps + tokens), Tool (catalogue).
- Tier 1 et Tier 2 du compilateur sont couverts par ces tables ; les fichiers references/ (Tier 3) ne sont PAS en base.
- À décider : lire les references sur disque (sans toucher au registre) ou créer une table ; traitement des skills needs_review dans l'index.
- count_tokens existe déjà dans registry/parser.py : à clarifier avec le Role 2 avant d'écrire le contrat.

## Incrément 3 : base et comptage de tokens (17/11/2026)
- Vérifié : la base de dev contient 13 AGENTS.md, 12 skills, 21 outils (cohérent avec l'arborescence).
- count_tokens (registry/parser.py) utilise tiktoken o200k_base : c'est une ESTIMATION (tokenizer OpenAI, pas Gemini). À écrire tel quel dans le rapport.
- Choix proposé : le compilateur appelle count_tokens(text) -> int ; si le Role 2 déplace la fonction, la signature reste identique.
- Non vérifié : tiktoken télécharge-t-il son vocabulaire au premier usage (risque pour le test d'installation sur machine vierge) ?

## Incrément 4 : décisions pour le contrat (17/11/2026)
- Constaté : 10 skills active, 2 needs_review (avertissements : outil d'écriture sur invoice-validation, outil non cité sur finding-report). 12 skills en base = aucun rejeté (déduction).
- Choix : les needs_review restent dans l'index Tier 1 ; references/ lues sur disque ; masquage dès 70 % du budget, autres évictions au-delà de 100 %.
- Choix de conception : le compilateur est une fonction pure (mêmes événements = même contexte), le Tier 2 est ajouté à la fin de l'historique à l'activation, pour garder le préfixe stable (KV-cache).
- Règle d'équipe (Ali) : si un blocage dépend d'un autre rôle, on le réalise en fichier provisoire puis on informe l'équipe.
## À signaler à l'équipe
- Role 4 : le skill finding-report (Compliance) déclare query_audit_log sans le citer dans son corps.
## Incrément 5 : contrat d'interface v0 (17/11/2026)
- Fait : docs/CONTRATS_INTERFACE.md (brouillon) : types partagés, compile_context, et ce qui est attendu des Roles 2 à 5.
- Pourquoi : les autres rôles sont bloqués tant que les noms de fonctions, entrées et sorties ne sont pas fixés.
- Non vérifié : rien du contrat n'est encore implémenté ni testé ; les noms d'apps (compiler, masking, engine, sync, bench) sont des propositions à confirmer.