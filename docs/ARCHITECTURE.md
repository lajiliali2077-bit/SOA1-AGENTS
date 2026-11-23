# Architecture orientée services (SOA)

## 1. Le problème en une phrase

Une IA lit un **contexte** (mesuré en **tokens**) avant de répondre. Si on lui envoie toute la documentation à chaque appel, elle devient plus chère, plus lente et moins précise. Notre **compilateur de contexte** lui envoie **seulement ce qui est utile, au bon moment**, et nous **mesurons** l'économie.

## 2. Définitions

| Terme | Définition simple | Dans notre projet |
|---|---|---|
| Service | Un composant indépendant, avec un rôle unique, qui expose une interface (API). | 7 applications Django (tableau ci-dessous) |
| API REST | Des adresses web qui reçoivent et renvoient du JSON (GET pour lire, POST pour agir). | Django REST Framework, `@api_view` |
| Contrat de service | Ce qu'un service promet : entrées, sorties, erreurs. | Chaque vue DRF documente ses entrées/sorties ; codes 400, 403, 404, 503 |
| Couplage faible | Un service n'a pas besoin de connaître le code interne d'un autre. | L'interface web ne parle qu'à l'API ; n8n ne parle qu'à l'API |
| Webhook | Une « sonnette » : un service appelle l'adresse d'un autre quand un événement arrive. | GitHub → Django (entrant), Django → n8n (sortant) |
| Orchestration | Un chef d'orchestre enchaîne plusieurs services. | Le service Agent enchaîne Compilateur → Gemini → Moteur → Outils |
| Contexte | Tout le texte envoyé à l'IA pour un appel. | Construit par `compiler/core.py` |
| Token | Morceau de mot ; le coût se compte en tokens. | Compté par Gemini (`count_tokens`) pour les mesures, par tiktoken pour le budget interne |
| Mode progressif | Notre compilateur : divulgation progressive, budget, masquage. | `compile_context(..., mode="progressive")` |
| Mode monolithique | Sans compilateur : tout est chargé à chaque appel. | `compile_context(..., mode="monolithic")` |

## 3. Les 7 services

| Service | App Django | Rôle | Interface |
|---|---|---|---|
| **Registre** | `registry` | Lit AGENTS.md, SKILL.md, `tools/*.yaml` ; valide (Pydantic) ; enregistre dans PostgreSQL | `GET /api/skills/`, `python manage.py index_skills` |
| **Compilateur** | `compiler` | Construit le contexte (3 niveaux, budget, masquage) ; mode progressif ou monolithique | `POST /api/compile/`, `POST /api/tokens/` |
| **Masquage** | `masking` | Garde les sorties d'outils complètes en base et les remplace par une ligne courte dans le contexte | `GET /api/observations/<id>/` |
| **Moteur déterministe** | `engine` | Garde (droits), exécuteur (appelle les outils), vérificateur (réponse finale) | fonctions Python appelées par l'Agent |
| **Outils** | `erp` | Les vraies fonctions métier sur la base de la boutique (commandes, clients, remboursements) | `GET /api/tools/`, `POST /api/tools/<nom>/` |
| **Agent et mesures** | `bench` | Orchestration d'une requête avec Gemini, mesure des tokens, tableau de bord | `GET /api/tasks/`, `POST /api/run/`, `GET /api/runs/`, page `/` |
| **Synchronisation** | `sync` | Webhook GitHub signé (HMAC) et appel n8n : réindexe le registre quand la doc change | `POST /api/sync/github/`, `POST /api/sync/n8n/` |

Services externes : **Google Gemini 3.5 Flash-Lite** (IA), **PostgreSQL** (stockage), **n8n** (automatisation), **GitHub** (source de la documentation).

## 4. Schéma d'architecture

```mermaid
flowchart LR
    UI[Interface web<br>page /] -->|REST| AGENT
    N8N[n8n] -->|REST POST /api/run/| AGENT
    AGENT[Service Agent<br>bench] --> COMP[Service Compilateur]
    AGENT -->|generate + count_tokens| GEMINI[Gemini 3.5 Flash-Lite]
    AGENT --> ENG[Moteur déterministe]
    ENG --> TOOLS[Service Outils<br>erp]
    COMP --> MASK[Service Masquage]
    COMP --> DB[(PostgreSQL)]
    TOOLS --> DB
    MASK --> DB
    AGENT --> DB
    AGENT -.->|webhook sortant| N8N
    GH[GitHub] -->|webhook signé HMAC| SYNC[Service Synchronisation]
    GH -->|webhook| N8N -->|jeton X-Sync-Token| SYNC
    SYNC --> REG[Service Registre] --> DB
```

## 5. Diagrammes de séquence

### Une requête choisie dans l'interface

```mermaid
sequenceDiagram
    participant U as Interface web
    participant A as Service Agent
    participant C as Compilateur
    participant G as Gemini
    participant M as Moteur (garde)
    participant O as Service Outils
    U->>A: POST /api/run/ {task_id: cs-01}
    A->>O: seed_demo() (données de départ)
    loop jusqu'à la réponse finale (12 appels max)
        A->>C: compile_context(historique, progressif)
        C-->>A: contexte (règles utiles + skill actif + outils autorisés)
        A->>G: count_tokens(contexte progressif) et count_tokens(contexte monolithique)
        A->>G: generate_content(contexte)
        G-->>A: une action JSON (+ tokens facturés)
        A->>M: format valide ? outil autorisé ? confirmation ?
        alt appel d'outil autorisé
            M->>O: get_order(...)
            O-->>A: résultat (observation, enregistrée)
        else refusé
            M-->>A: refus (confirmation_required, ...)
        end
    end
    A-->>U: étapes, tokens par étape, réponse, vérifications
    A--)n8n: webhook « exécution terminée » (facultatif)
```

### Synchronisation de la documentation

```mermaid
sequenceDiagram
    participant GH as GitHub
    participant S as Service Synchronisation
    participant R as Service Registre
    participant DB as PostgreSQL
    GH->>S: POST /api/sync/github/ + signature X-Hub-Signature-256
    S->>S: recalcul HMAC-SHA256 avec le secret partagé
    alt signature fausse
        S-->>GH: 403
    else signature correcte, push sur main
        S->>R: index_all()
        R->>DB: remplace skills, outils, AGENTS.md
        S-->>GH: 200 {status: ok}
    end
```

## 6. Comment on mesure l'économie de tokens

À **chaque appel** à Gemini pendant une exécution :
1. le service Agent construit le contexte **progressif** (celui qui est envoyé) ;
2. il construit aussi le contexte **monolithique** à partir du **même historique** (tous les AGENTS.md, tous les skills, toutes les annexes, tous les outils, aucune sortie masquée) ;
3. il demande à **Gemini lui-même** de compter les deux (`count_tokens`, gratuit, sans génération) ;
4. il enregistre aussi les tokens **réellement facturés** par Gemini (`usage_metadata`).

Les sommes sont stockées dans la table `Run` (`prog_tokens`, `mono_tokens`, `input_tokens`, `output_tokens`) et affichées par le tableau de bord. Les deux modes reçoivent exactement le même historique : seule la façon de construire le contexte change, donc la comparaison est juste.

Il est aussi possible d'exécuter réellement une requête en mode monolithique (bouton « Sans compilateur » de l'interface, ou `python manage.py benchmark --real-monolithic`).

## 7. Les tables PostgreSQL

| Service | Tables |
|---|---|
| Registre | `AgentsFile`, `Skill`, `Tool` |
| Masquage | `Observation` |
| Outils (boutique) | `Customer`, `Product`, `Order`, `OrderLine`, `TrackingEvent`, `Refund` |
| Agent | `Run` (une exécution, ses étapes et ses mesures) |
| Synchronisation | `SyncEvent` |
