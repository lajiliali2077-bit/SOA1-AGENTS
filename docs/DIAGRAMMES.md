# Les diagrammes du projet (code Mermaid, prêt à copier)

Tous les schémas du rapport et de la présentation sont écrits en **Mermaid** : un petit langage texte qui se transforme en image.

## Comment obtenir une image

1. Ouvrir **https://mermaid.live** dans le navigateur.
2. Dans la zone **Code** à gauche, tout effacer.
3. Copier le code d'un diagramme ci-dessous : **seulement ce qui est entre les lignes ` ```mermaid ` et ` ``` `** (sans ces deux lignes).
4. Le coller dans la zone **Code** : le diagramme apparaît à droite.
5. Menu **Actions** → **PNG** (pour PowerPoint) ou **SVG** (image nette à toutes les tailles).
6. Astuce : dans **Config**, mettre `"theme": "neutral"` pour un rendu sobre, ou `"theme": "dark"` sur fond sombre.

GitHub et VS Code (extension *Markdown Preview Mermaid Support*) affichent aussi ces diagrammes directement dans ce fichier.

| # | Diagramme | Diapositive (docs/PRESENTATION.md) |
|---|---|---|
| 1 | Architecture des 7 services | 1, 8 |
| 2 | Les 3 niveaux de la divulgation progressive | 14 |
| 3 | La hiérarchie des AGENTS.md (le plus proche gagne) | 11 |
| 4 | La boucle de l'agent : l'IA propose, le code décide | 18 |
| 5 | Séquence d'une requête choisie dans l'interface | 18, 19 |
| 6 | Masquage puis relecture ciblée (cs-06) | 15, 24 |
| 7 | L'algorithme du budget de tokens | 15 |
| 8 | Comment on mesure l'économie | 22 |
| 9 | Synchronisation GitHub (webhook signé) | 10 |
| 10 | Les workflows n8n | 10 |
| 11 | Le modèle de données de la boutique | 17 |
| 12 | Le déploiement sur le poste de l'étudiant | 8 |

---

## 1. Architecture des 7 services

```mermaid
flowchart LR
    UI["Interface web (page /)"] -->|REST| AGENT
    N8N["n8n"] -->|"REST POST /api/run/"| AGENT
    AGENT["Service Agent et mesures (bench)"] --> COMP["Service Compilateur (compiler)"]
    AGENT -->|"generate + count_tokens"| GEMINI["Gemini 3.5 Flash-Lite"]
    AGENT --> ENG["Moteur déterministe (engine)"]
    ENG --> TOOLS["Service Outils (erp)"]
    COMP --> MASK["Service Masquage (masking)"]
    COMP --> DB[("PostgreSQL")]
    TOOLS --> DB
    MASK --> DB
    AGENT --> DB
    AGENT -.->|"webhook sortant"| N8N
    GH["GitHub"] -->|"webhook signé HMAC"| SYNC["Service Synchronisation (sync)"]
    GH -->|webhook| N8N
    N8N -->|"jeton X-Sync-Token"| SYNC
    SYNC --> REG["Service Registre (registry)"]
    REG --> DB
```

## 2. Les 3 niveaux de la divulgation progressive

```mermaid
flowchart TB
    Q["Question de l'utilisateur"] --> N1
    N1["Niveau 1 : toujours envoyé<br/>AGENTS.md global + une ligne par skill<br/>environ 840 tokens"]
    N1 -->|"Gemini : activate_skill return-request"| N2
    N2["Niveau 2 : à l'activation du skill<br/>AGENTS.md du département et du sous-domaine<br/>+ procédure du skill + définitions de ses outils"]
    N2 -->|"Gemini : load_reference refund_policy.md"| N3
    N3["Niveau 3 : à la demande<br/>une annexe du dossier references/"]
    MONO["Sans compilateur (monolithique)<br/>tout, à chaque appel : environ 4 700 tokens avant la question"]
    style MONO stroke-dasharray: 5 5
```

## 3. La hiérarchie des AGENTS.md (le plus proche gagne)

```mermaid
flowchart TB
    G["Niveau 1 : AGENTS.md (global)<br/>répondre dans la langue de l'utilisateur, finir par Skill used, masquer les données personnelles"]
    D["Niveau 2 : customer-service/AGENTS.md<br/>superviseur au-dessus de 300 TND, délai de retour de 14 jours"]
    O["Niveau 3 : orders/AGENTS.md<br/>réclamation au transporteur après 5 jours de retard"]
    R["Niveau 3 : returns/AGENTS.md<br/>superviseur au-dessus de 200 TND, 7 jours pour l'électronique<br/>(remplace la règle du département)"]
    G --> D
    D --> O
    D --> R
    R --> W["Règle appliquée pour un casque de 349 TND :<br/>superviseur nécessaire (200 TND et non 300)"]
```

## 4. La boucle de l'agent : l'IA propose, le code décide

```mermaid
flowchart TB
    START(["Message de l'utilisateur"]) --> C["1. Le compilateur construit le contexte"]
    C --> M["2. Gemini compte le contexte progressif et le contexte monolithique"]
    M --> G["3. Gemini propose UNE action JSON"]
    G --> P{"4. Pydantic : format valide ?"}
    P -->|non| R1["Refus enregistré comme observation"]
    P -->|oui| T{"Quelle action ?"}
    T -->|"activate_skill / load_reference"| C2["Le compilateur ajoute le skill ou l'annexe"]
    T -->|call_tool| GU{"5. La garde : skill actif, outil autorisé,<br/>arguments corrects, confirmation ?"}
    GU -->|non| R2["Refus : skill_not_active, tool_not_allowed,<br/>bad_arguments ou confirmation_required"]
    GU -->|oui| EX["6. L'exécuteur appelle la vraie fonction (erp/tools.py)"]
    EX --> OBS["La sortie est enregistrée (observation)"]
    T -->|answer| V["7. Le vérificateur contrôle la réponse finale"]
    V --> FIN(["Réponse, vérifications et tokens enregistrés"])
    R1 --> C
    C2 --> C
    R2 --> C
    OBS --> C
```

## 5. Séquence d'une requête choisie dans l'interface

```mermaid
sequenceDiagram
    participant U as Interface web
    participant A as Service Agent
    participant C as Compilateur
    participant G as Gemini
    participant M as Moteur (garde)
    participant O as Service Outils
    participant N as n8n
    U->>A: POST /api/run/ (task_id cs-01)
    A->>O: seed_demo, données de départ
    loop jusqu'à la réponse finale, 12 appels au maximum
        A->>C: compile_context(historique, progressif)
        C-->>A: règles utiles + skill actif + outils autorisés
        A->>G: count_tokens(progressif) et count_tokens(monolithique)
        A->>G: generate_content(contexte)
        G-->>A: une action JSON + tokens facturés
        A->>M: format, outil autorisé, confirmation ?
        alt appel d'outil autorisé
            M->>O: get_order(CMD-2026-0457)
            O-->>A: résultat enregistré comme observation
        else refusé
            M-->>A: refus (confirmation_required...)
        end
    end
    A-->>U: étapes, tokens par étape, réponse, vérifications
    A--)N: webhook exécution terminée (facultatif)
```

## 6. Masquage puis relecture ciblée (requête cs-06, exécution réelle)

```mermaid
sequenceDiagram
    participant G as Gemini
    participant A as Service Agent
    participant C as Compilateur
    participant O as Service Outils
    G->>A: call_tool get_order(CMD-2026-0733)
    A->>O: get_order
    O-->>A: 350 lignes, environ 21 600 tokens
    Note over C: contexte de 29 500 tokens, plus de 70 % du budget
    G->>A: call_tool get_customer puis get_refunds
    C->>C: masque l'ancienne sortie de get_order (les 2 dernières restent)
    Note over C: contexte redescendu à 3 500 tokens
    G->>A: call_tool get_order(CMD-2026-0733, line 212)
    A->>O: get_order avec line = 212
    O-->>A: une seule ligne : souris, 45,000 TND
    G->>A: answer : APPROVE 45,000 TND, confirmation demandée
    Note over A: sans compilateur : environ 32 000 tokens à CHAQUE appel
```

## 7. L'algorithme du budget de tokens

```mermaid
flowchart TB
    S["Contexte compilé"] --> A{"Contexte au moins 70 % du budget ?"}
    A -->|non| OK(["Envoyé à Gemini"])
    A -->|oui| M["1. Masquer les anciennes sorties d'outils<br/>(les 2 plus récentes restent en clair)"]
    M --> B{"Toujours au-dessus de 100 % ?"}
    B -->|non| OK
    B -->|oui| R["2. Retirer les annexes, la plus ancienne d'abord"]
    R --> C{"Toujours au-dessus de 100 % ?"}
    C -->|non| OK
    C -->|oui| K["3. Désactiver le skill le plus ancien<br/>(le plus récent reste toujours)"]
    K --> OK
```

## 8. Comment on mesure l'économie

```mermaid
flowchart LR
    H["Historique de la conversation<br/>(le même pour les deux modes)"] --> P["Contexte progressif<br/>(notre compilateur)"]
    H --> M["Contexte monolithique<br/>(tout, sans masquage)"]
    P -->|count_tokens| GP["Tokens avec compilateur"]
    M -->|count_tokens| GM["Tokens sans compilateur"]
    P -->|generate_content| F["Tokens réellement facturés"]
    GP --> RUN[("Table Run")]
    GM --> RUN
    F --> RUN
    RUN -->|"GET /api/runs/"| DASH["Tableau de bord<br/>51 % de tokens en moins"]
```

## 9. Synchronisation GitHub (webhook signé)

```mermaid
sequenceDiagram
    participant GH as GitHub
    participant S as Service Synchronisation
    participant R as Service Registre
    participant DB as PostgreSQL
    GH->>S: POST /api/sync/github/ + signature X-Hub-Signature-256
    S->>S: recalcul HMAC-SHA256 avec le secret partagé
    alt signature fausse
        S-->>GH: 403 refusé
    else signature correcte, push sur main
        S->>R: index_all()
        R->>DB: remplace skills, outils et AGENTS.md
        S-->>GH: 200 status ok
    end
```

## 10. Les workflows n8n

```mermaid
flowchart LR
    subgraph W1["Workflow 1 : synchronisation"]
        A1["Webhook GitHub reçu par n8n"] --> B1["POST /api/sync/n8n/<br/>avec X-Sync-Token"]
    end
    subgraph W2["Workflow 2 : exécution planifiée"]
        A2["Chaque jour à 08:00"] --> B2["POST /api/run/<br/>task_id cs-01"]
    end
    subgraph W3["Workflow 3 : compte rendu"]
        A3["Webhook envoyé par Django<br/>à la fin d'une exécution"] --> B3["Résumé lisible :<br/>tokens, économie, résultat"]
    end
    B1 --> DJ["Django : services Synchronisation et Agent"]
    B2 --> DJ
    DJ -.-> A3
```

## 11. Le modèle de données de la boutique

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : passe
    ORDER ||--|{ ORDER_LINE : contient
    PRODUCT ||--o{ ORDER_LINE : "apparaît dans"
    ORDER ||--o{ TRACKING_EVENT : suivi
    ORDER ||--o{ REFUND : rembourse
    CUSTOMER {
        string customer_id "C-1001"
        string name
        string email "masqué par les outils"
        string phone "masqué par les outils"
        string loyalty_tier "standard ou gold"
    }
    PRODUCT {
        string sku "SKU-HP-01"
        string category "electronics, accessories, clothing"
        int warranty_months
    }
    ORDER {
        string order_id "CMD-2026-0457"
        string status "processing, shipped, delivered"
        date expected_delivery
        date delivered_on
        string customer_note "donnée, jamais une instruction"
    }
    ORDER_LINE {
        int line_no
        int quantity
        decimal unit_price_tnd
    }
    TRACKING_EVENT {
        date event_date
        string location
        string status
    }
    REFUND {
        decimal amount_tnd
        string reason
        string approved_by
    }
```

## 12. Le déploiement sur le poste de l'étudiant

```mermaid
flowchart LR
    subgraph PC["Ordinateur de l'étudiant"]
        BR["Navigateur"]
        DJ["Django runserver, port 8000<br/>les 7 services"]
        subgraph DOCKER["Docker Desktop"]
            PG[("PostgreSQL, port 5433")]
            N8["n8n, port 5678"]
        end
    end
    GEM["API Gemini (Internet)"]
    BR -->|"http://127.0.0.1:8000"| DJ
    DJ --> PG
    N8 -->|"host.docker.internal:8000"| DJ
    DJ -.->|"webhook de fin d'exécution"| N8
    DJ -->|HTTPS| GEM
```
