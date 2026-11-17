# Contrats d'interface, version 0 (brouillon du Role 1, à valider par l'équipe)

Règle : on change un nom ICI avant de coder, jamais après. Rien n'est implémenté.
Les tokens sont des ESTIMATIONS (tiktoken o200k_base, tokenizer OpenAI, pas celui de Gemini).

## 0. Une app Django par service (noms proposés)

| Service | App | Role |
|---|---|---|
| Compilateur de contexte | compiler | 1 |
| Masquage des observations, modèle Observation | masking | 2 |
| Moteur déterministe (garde, vérificateur, exécuteur) | engine | 3 |
| Synchronisation (webhook, SyncEvent) | sync | 4 |
| Client Gemini, benchmark en ligne, tableau de bord | bench | 5 |
| Registre (existant) | registry | - |

## 1. Types partagés (définis par le Role 1 dans compiler/types.py)

~~~python
@dataclass(frozen=True)
class Event:            # un élément de l'historique (on n'ajoute qu'à la fin)
    kind: str           # "user" | "assistant" | "activate_skill" | "load_reference" | "observation"
    text: str = ""      # texte du message, ou sortie complète de l'outil
    skill: str = ""     # activate_skill, load_reference : nom du skill
    filename: str = ""  # load_reference : fichier du dossier references/ du skill
    tool: str = ""      # observation : nom de l'outil appelé
    obs_id: str = ""    # observation : identifiant donné par le Role 2 ("obs-0007")

@dataclass(frozen=True)
class ContextItem:      # un bloc du contexte compilé
    tier: int           # 1, 2, 3, ou 0 pour la conversation
    kind: str           # "agents" | "skill_index" | "skill_body" | "reference"
                        # | "user" | "assistant" | "observation" | "masked"
    text: str
    tokens: int
    source: str = ""    # chemin du fichier, nom du skill ou obs_id

@dataclass(frozen=True)
class CompileResult:
    text: str               # contexte complet, à envoyer à Gemini
    items: list             # liste de ContextItem (sert à mesurer la composition des tokens)
    tokens: int             # total estimé (texte + définitions des outils)
    budget: int
    prefix_tokens: int      # taille du Tier 1 (préfixe stable)
    active_skills: list     # noms, du plus ancien au plus récent (2 maximum)
    allowed_tools: list     # outils autorisés par les skills actifs
    tool_tokens: int        # somme de Tool.tokens des outils autorisés (déjà dans tokens)
    compacted: bool         # True si une éviction ou un masquage a eu lieu
    evictions: list         # ex. "masked:obs-0003", "unloaded:<fichier>", "deactivated:<skill>"
~~~

## 2. Offert par le Role 1 : compilateur (app compiler)

~~~python
compile_context(events: list[Event], budget: int = 6000, mode: str = "progressive") -> CompileResult
~~~

- Fonction pure : mêmes événements = même résultat. Elle lit seulement la base du registre.
- Tier 1 en premier (AGENTS.md global + index de tous les skills active et needs_review), jamais évincé.
- activate_skill : ajoute À LA FIN les AGENTS.md du département et du sous-domaine, puis le corps du skill (Tier 2). 2 skills actifs au maximum.
- load_reference : ajoute à la fin le fichier lu sur disque à partir de Skill.path (Tier 3).
- Éviction : masquage (service Role 2, dès 70 % du budget), puis références déchargées (la plus ancienne d'abord), puis skill le plus ancien désactivé (au-delà de 100 %).
- Append-only : si compacted vaut False, le texte pour events[:n] est un préfixe du texte pour events[:n+1].
- mode="monolithic" : charge tous les AGENTS.md, tous les corps de skills et tous les outils, sans éviction (sert de comparaison au benchmark).

## 3. Attendu du Role 2 : tokens et masquage (app masking)

~~~python
count_tokens(text: str) -> int                 # existe : registry.parser ; même signature si déplacée
record_observation(tool: str, output: str) -> str     # enregistre en base, retourne "obs-0007"
mask_observations(items: list, budget: int) -> list   # dès 70 % du budget, remplace toutes les observations sauf les 2 dernières
                                                       # par un item kind="masked" : [sortie masquée : <outil>, <n> lignes, <n> tokens, id obs-0007]
recall_observation(obs_id: str) -> str         # retourne la sortie originale complète
~~~

## 4. Attendu du Role 3 : moteur déterministe (app engine)

~~~python
check_tool_call(tool: str, arguments: dict, result: CompileResult, confirmed: bool = False) -> GuardDecision
# GuardDecision : allowed (bool), code, message
# codes : ok | skill_not_active | tool_not_allowed | bad_arguments | confirmation_required
execute_tool(department: str, tool: str, arguments: dict) -> str    # lit fixtures/<département>.json
~~~

La signature du vérificateur de règles (IBAN masqué, montants, ligne « Skill used: », décision, seuil) est définie par le Role 3 ; le compilateur n'en dépend pas.

## 5. Role 4 : synchronisation

- Après git pull, le webhook appelle registry.indexer.index_all() (existe déjà).
- Le compilateur relit la base à chaque appel : aucun cache à vider.

## 6. Role 5 : API et client Gemini (vues JSON simples, sans Django REST Framework)

- GET /api/skills/ : liste JSON (name, description, department, subdomain, status, allowed_tools, meta_tokens, body_tokens).
- POST /api/compile/ : entrée {"events": [...], "budget": 6000, "mode": "progressive"}, sortie : CompileResult en JSON.
- Boucle d'un tour : compile_context -> Gemini -> check_tool_call -> execute_tool -> record_observation -> nouvel Event "observation".