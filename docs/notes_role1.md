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

## Incrément 6 : compilateur v1 (17/11/2026)
- Fait : app compiler (types.py, core.py, test_core.py). compile_context construit le Tier 1 (AGENTS.md global + index des skills) et ajoute les messages user/assistant.
- Pourquoi : fonction pure, blocs ajoutés à la fin séparés par une ligne vide, donc le texte du tour N est le début du texte du tour N+1 (test automatique, préfixe stable pour le cache KV).
- Pas encore fait (lève NotImplementedError) : activation de skill, references, observations, éviction, mode monolithique.
- Choix : l'app n'est pas ajoutée à INSTALLED_APPS (pas de modèle) : settings.py reste intact.

## Incrément 7 : activation d'un skill, Tier 2 (17/11/2026)
- Fait : l'événement activate_skill ajoute à la fin l'AGENTS.md du département, celui du sous-domaine, puis le corps du skill (tier 2). Remplit active_skills, allowed_tools et tool_tokens.
- Pourquoi : le plus spécifique est le plus proche de la fin, ce qui respecte la règle « le fichier le plus proche a priorité ». Réactiver un skill, ou un second skill du même sous-domaine, n'ajoute aucun doublon : le contexte reste append-only (test sur les 5 tours).
- Pas encore fait : 3e skill actif (lève NotImplementedError, la désactivation viendra avec l'éviction), load_reference, observations, éviction, mode monolithique.
- Choix : les tests se lancent avec « python manage.py test compiler » ; pytest n'est pas dans requirements.txt (configuration pytest à faire plus tard).

## Incrément 9 : mode monolithique (17/11/2026)
- Fait : compile_context(mode="monolithic") charge tous les AGENTS.md, tous les corps de skills et tous les outils, sans éviction. Même liste d'événements rejouable dans les deux modes. 32 tests.
- Pourquoi : c'est la référence du benchmark. Le but est de mesurer les tokens économisés par la divulgation progressive. Le budget peut être dépassé : c'est ce qu'on veut montrer.
- Choix : les références (Tier 3) ne sont pas chargées en monolithique (contrat), donc la comparaison est prudente. Les tiers sont les mêmes qu'en mode progressif pour comparer la composition.
- Pas encore fait : observations, éviction (dont le 3e skill actif).

## Incrément 10 : éviction sans masquage (17/11/2026)
- Fait : un 3e skill actif désactive le plus ancien (corps, références, AGENTS.md devenus inutiles). Si le budget est dépassé, on décharge les références (la plus ancienne d'abord), puis on désactive le skill le plus ancien. Le Tier 1 et la conversation ne sont jamais évincés. evictions : "unloaded:<fichier>", "deactivated:<skill>" ; compacted vaut True. 14 tests dans test_eviction.py.
- Pourquoi : l'éviction garde le contexte dans le budget sans jamais toucher à l'essentiel. Le budget peut rester dépassé si on ne peut plus rien retirer : on le dit au lieu de tricher.
- Choix : la référence qu'on vient de charger est protégée pendant son événement. Le masquage des observations (Role 2) n'existe pas encore : un point d'accroche est prévu dans _enforce_budget.
- Compromis assumé : retirer un bloc au milieu casse le préfixe KV-cache. C'est pourquoi l'éviction n'a lieu qu'en cas de besoin, et compacted le signale.
- Pas encore fait : masquage des observations et événement "observation".
- Le Role 2 devra livrer mask_observations avec la signature du contrat, et je la brancherai dans _enforce_budget.

## Incrément 10 : compilateur utilisable par toute l'équipe (17/11/2026)
- Fait : événement observation (sortie complète ajoutée à la fin), désactivation du plus ancien skill au 3e skill actif, conversion JSON (serialize.py) pour l'API, mode d'emploi pour les 4 autres rôles. 45 tests. Plus aucune erreur « pas encore implémenté » dans le compilateur.
- Pourquoi : prioriser ce qui débloque les autres rôles (boucle du Role 5, garde du Role 3, masquage du Role 2) avant l'éviction par budget, qui ne bloque personne.
- Choix : en désactivant un skill on garde ses AGENTS.md (l'autre skill actif peut en dépendre). Le contexte n'est plus un préfixe stable dans ce cas, d'où compacted=True (prévu par le contrat).
- Pas encore fait : masquage des observations (dépend du Role 2), éviction par budget (références, puis skill), pytest.