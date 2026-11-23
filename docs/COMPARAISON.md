# Matrice de comparaison multicritère

Notes : 1 = faible, 3 = fort, pour notre besoin (projet étudiant, démonstration, Django). Les sources sont listées en bas.

## 1. Comment donner la documentation à l'IA ?

| Critère | Tout envoyer (monolithique) | Recherche RAG (base vectorielle) | Divulgation progressive (notre choix) |
|---|---|---|---|
| Tokens envoyés | 1 (tout, à chaque appel) | 2 | 3 (seulement l'utile) |
| Précision sur un long contexte [3][4] | 1 (risque « lost in the middle ») | 2 | 3 |
| Simplicité à mettre en place | 3 | 1 (embeddings, base vectorielle) | 2 |
| L'IA choisit elle-même ce qu'elle lit | 1 | 1 (choix fait par la recherche) | 3 (activate_skill, load_reference) |
| Format standard des fichiers [1][2] | 2 | 1 | 3 (AGENTS.md + SKILL.md) |
| Mesuré dans notre projet | 413 345 tokens pour 7 tâches | non testé | 181 063 tokens (56 % de moins) |

## 2. Comment déclencher la synchronisation ?

| Critère | Webhook natif Django | n8n | Celery |
|---|---|---|---|
| Installation | 3 (rien à ajouter) | 2 (un conteneur Docker) | 1 (broker Redis ou RabbitMQ obligatoire [7]) |
| Sécurité | 3 (signature HMAC vérifiée [5]) | 2 (jeton partagé) | 2 |
| Visuel, facile à expliquer | 1 | 3 (workflow dessiné [6]) | 1 |
| Tâches longues en arrière-plan | 1 | 2 | 3 |
| Notre choix | oui, chemin principal | oui, variante visuelle | non (trop lourd pour le besoin) |

## 3. Comment vérifier les sorties de l'IA ?

| Critère | pytest | Pydantic v2 | sqlglot | OPA (opa test) |
|---|---|---|---|---|
| Ce que ça vérifie | le comportement du code et des tâches [8] | le format JSON des réponses [9] | des requêtes SQL (arbre syntaxique) [10] | des politiques écrites en Rego [11] |
| Utile pour nous | 3 | 3 | 1 (l'IA ne génère pas de SQL) | 2 (nos règles tiennent en Python) |
| Difficulté | 1 | 1 | 2 | 3 (nouveau langage) |
| Notre choix | oui (36 tests) | oui (réponses IA, tâches, en-têtes SKILL.md, outils) | non | non |

## Sources (vérifiées le 2026-11-23)

1. AGENTS.md, format ouvert, « the closest AGENTS.md to the edited file wins » : https://agents.md/
2. Agent Skills, spécification (niveaux ~100 tokens, < 5000 tokens, ressources à la demande ; SKILL.md < 500 lignes) : https://agentskills.io/specification
3. Anthropic, *Effective context engineering for AI agents* (context rot, chargement « just in time », effacement des résultats d'outils) : https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
4. N. F. Liu et al., *Lost in the Middle: How Language Models Use Long Contexts*, 2023 : https://arxiv.org/abs/2307.03172
5. GitHub Docs, *Validating webhook deliveries* (en-tête X-Hub-Signature-256, HMAC-SHA256, comparaison à temps constant) : https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
6. n8n Docs, nœud Webhook : https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/
7. Celery, introduction (broker RabbitMQ ou Redis nécessaire) : https://docs.celeryq.dev/en/stable/getting-started/introduction.html
8. Django, tests (`manage.py test`) : https://docs.djangoproject.com/en/6.1/topics/testing/overview/
9. Pydantic, validation JSON (`model_validate_json`) : https://pydantic.dev/docs/validation/latest/concepts/json/
10. sqlglot (analyse SQL en arbre syntaxique) : https://github.com/tobymao/sqlglot
11. Open Policy Agent, *Policy testing* (`opa test`, langage Rego) : https://www.openpolicyagent.org/docs/policy-testing
12. Google AI Studio, sortie structurée JSON de Gemini : https://aistudio.google.com/docs/structured-output
13. tiktoken (comptage de tokens) : https://github.com/openai/tiktoken
