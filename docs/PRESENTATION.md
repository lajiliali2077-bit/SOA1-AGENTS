# Plan des diapositives (PowerPoint)

Une idée par diapositive. Les schémas viennent de `docs/ARCHITECTURE.md` (copier le code Mermaid dans https://mermaid.live, puis exporter en PNG).

| # | Titre | Contenu | Source |
|---|---|---|---|
| 1 | Titre | Nom du projet, équipe, matière SOA | - |
| 2 | Le problème | L'IA a une mémoire limitée : trop de texte la rend lente, chère et moins précise (context rot) | COMPARAISON.md [3][4] |
| 3 | Notre idée | Donner à l'IA un sommaire, puis le chapitre, puis l'annexe, seulement si besoin | ARCHITECTURE.md §2 |
| 4 | Définitions | AGENTS.md, SKILL.md, divulgation progressive, masquage, budget de tokens | ARCHITECTURE.md §2 |
| 5 | AGENTS.md hiérarchique | Global, département, sous-domaine ; exemple 10000 TND remplacé par 5000 TND | `departments/finance/` |
| 6 | Un SKILL.md | En-tête (name, description « Use when ») + procédure + dossier references/ | `invoice-validation/SKILL.md` |
| 7 | Architecture SOA | Schéma des 6 services et de PostgreSQL | ARCHITECTURE.md §4 |
| 8 | Un tour de l'agent | Diagramme de séquence : compiler, IA, Pydantic, garde, exécuteur, vérificateur | ARCHITECTURE.md §5 |
| 9 | L'IA est encadrée | Tableau des contrôles déterministes (Pydantic, garde, vérificateur, pytest) | ARCHITECTURE.md §7 |
| 10 | Synchronisation | GitHub, webhook signé HMAC (ou n8n), index_all | ARCHITECTURE.md §5 |
| 11 | Installation | Les commandes, de `git clone` à `runserver` | README.md |
| 12 | Commandes CLI | index_skills, run_task, demo, benchmark, check_gemini, pytest | README.md |
| 13 | Résultats chiffrés | Graphique en barres progressif contre monolithique par tâche (depuis `docs/benchmark.csv`) | BENCHMARK.md |
| 14 | Les pièges testés | Écriture sans confirmation, injection, hors périmètre, sortie énorme | `tasks/finance/` |
| 15 | Comparaison | Les 3 matrices multicritères et les sources | COMPARAISON.md |
| 16 | Démo | Plan A Gemini, plan B hors ligne | DEMO.md |
| 17 | Limites | Tokens estimés avec tiktoken (pas le tokenizer de Gemini) ; outils simulés ; un seul département complet | - |
| 18 | Conclusion | 56 % de tokens en moins, 7 tâches sur 7 réussies, 36 tests | BENCHMARK.md |

## Phrases simples pour l'oral

- « Le compilateur, c'est le bibliothécaire : il ne donne à l'IA que le livre et la page dont elle a besoin. »
- « L'IA propose, le code décide : chaque action passe par la garde avant d'être exécutée. »
- « Une sortie de 350 lignes devient une ligne : le texte complet reste en base, on peut le relire avec son identifiant. »
- « Si GitHub change un skill, le webhook met la base à jour ; une fausse signature est refusée. »
