# Les skills : explication complète

Ce document explique **ce qu'est un skill**, **comment il est écrit**, **comment l'application le charge** et **comment l'IA (Gemini) l'utilise**, sur un exemple réel du projet. Aucune connaissance en IA n'est nécessaire.

---

## 1. L'idée en une image

Un nouvel employé du service client ne lit pas les 300 pages de procédures le premier jour. On lui donne :
1. **un sommaire** : « voici les 6 tâches que tu sauras faire » ;
2. **la fiche de la tâche** quand il en a besoin : « remboursement : étape 1, étape 2… » ;
3. **une annexe** si la fiche le demande : « grille des délais de retour ».

Un **skill**, c'est exactement cette **fiche de tâche**, écrite pour l'IA. Notre **compilateur de contexte** est la personne qui donne la bonne fiche au bon moment.

---

## 2. Où sont les skills ?

```
departments/
  customer-service/                      ← le département (Service client)
    AGENTS.md                            ← règles du département (niveau 2)
    orders/                              ← sous-domaine « commandes et livraisons »
      AGENTS.md                          ← règles du sous-domaine (niveau 3)
      skills/
        order-tracking/SKILL.md          ← un skill
        order-tracking/references/carriers.md   ← son annexe
        customer-summary/SKILL.md
        delivery-complaint/SKILL.md
    returns/                             ← sous-domaine « retours et remboursements »
      AGENTS.md
      skills/
        return-request/SKILL.md
        return-request/references/refund_policy.md
        warranty-claim/SKILL.md
        exchange-request/SKILL.md
```

Le chemin du fichier suffit à savoir à quel **département** et à quel **sous-domaine** appartient un skill.

---

## 3. Les 6 skills du Service client

| Skill | Sous-domaine | Quand l'IA l'utilise | Outils autorisés |
|---|---|---|---|
| `order-tracking` | orders | « Où est ma commande ? », colis en retard | get_order, track_shipment, get_customer |
| `customer-summary` | orders | « Résume le compte du client C-1001 » | get_customer, search_orders |
| `delivery-complaint` | orders | Réclamation au transporteur (colis perdu, en retard) | get_order, track_shipment |
| `return-request` | returns | Demande de remboursement, article manquant | get_order, get_customer, get_refunds, calculate, **create_refund** |
| `warranty-claim` | returns | Produit en panne : encore sous garantie ? | get_order, get_product, calculate |
| `exchange-request` | returns | Échange de taille ou de couleur | get_order, get_customer, get_refunds |

`create_refund` est le seul **outil d'écriture** (il enregistre un remboursement dans la base). Les autres ne font que lire.

---

## 4. Anatomie d'un fichier SKILL.md

Un skill est un fichier texte en Markdown en **deux parties**. Exemple simplifié de `return-request` :

```markdown
---
name: return-request
description: Decide whether a return or refund request can be accepted ... Use when the user asks to accept, check or refund a return ...
allowed-tools: get_order get_customer get_refunds calculate create_refund
---

# Return request

## Procedure
1. Retrieve the order with get_order ...
2. Retrieve the customer with get_customer ...
3. Choose the return window with the returns rules ...
...
8. Only after an explicit confirmation, call create_refund.

## Answer template
Decision: APPROVE, REJECT or HOLD
Amount: <amount> TND
...
```

### Partie 1 : l'en-tête (entre les deux lignes `---`)

| Champ | Rôle | Règle vérifiée par le registre |
|---|---|---|
| `name` | Le nom du skill | minuscules et tirets, identique au nom du dossier |
| `description` | **Quand** utiliser ce skill. C'est la seule partie que l'IA voit au départ. | doit contenir « Use when » |
| `allowed-tools` | Les outils que l'IA a le droit d'appeler avec ce skill | chaque outil doit exister dans `tools/*.yaml` et être autorisé pour le département |

### Partie 2 : le corps (la procédure)

C'est le mode d'emploi, étape par étape, avec un **modèle de réponse** (*Answer template*). L'IA ne le lit **que si elle active le skill**.

> Pourquoi en anglais ? Les modèles d'IA suivent un peu mieux des consignes en anglais, et c'est l'usage dans les fichiers AGENTS.md / SKILL.md. Les réponses à l'utilisateur restent en français (règle du AGENTS.md global).

---

## 5. Étape A : le registre lit et vérifie les skills

Commande : `python manage.py index_skills` (fichier `registry/loader.py`).

Pour chaque `SKILL.md`, le registre :
1. lit l'en-tête et le vérifie avec **Pydantic** (format du nom, longueur de la description) ;
2. vérifie chaque outil de `allowed-tools` ;
3. donne un **statut** :

| Statut | Quand | Conséquence |
|---|---|---|
| `rejected` | outil inconnu, outil interdit au département, en-tête invalide | le skill n'est **pas** enregistré : l'IA ne le verra jamais |
| `needs_review` | le skill a un outil d'écriture, ou « Use when » manque, ou corps trop long | enregistré, mais signalé pour une relecture humaine |
| `active` | tout est correct | enregistré |

Exemple réel : `return-request` est `needs_review` parce qu'il peut appeler `create_refund` (écriture).

4. enregistre le skill dans **PostgreSQL** (table `Skill`), avec son nombre de tokens.

Quand quelqu'un modifie un skill sur GitHub, le **webhook** (ou n8n) relance automatiquement cette étape : la base est toujours à jour.

---

## 6. Étape B : le compilateur donne le skill à l'IA, par niveaux

Fichier `compiler/core.py`. C'est la **divulgation progressive** :

| Niveau | Ce que l'IA reçoit | Quand |
|---|---|---|
| **1** | le AGENTS.md global + **une ligne par skill** (nom + description) | toujours, dès la première question |
| **2** | les AGENTS.md du département et du sous-domaine + **le corps du skill** + **les définitions de ses outils** | quand l'IA répond `{"action": "activate_skill", "skill": "return-request"}` |
| **3** | une **annexe** du dossier `references/` | quand l'IA répond `{"action": "load_reference", "skill": "return-request", "filename": "refund_policy.md"}` |

Mesures réelles du projet (comptées par Gemini) :
- au démarrage, avec notre compilateur : environ **840 tokens** (niveau 1 seulement) ;
- sans compilateur (tout charger) : environ **4 700 tokens**, avant même la question.

### L'ordre des règles : « le plus proche gagne »

Quand un skill est activé, les règles sont ajoutées dans cet ordre : **global → département → sous-domaine**. La règle du sous-domaine est lue en dernier, et elle dit explicitement qu'elle remplace celle du département :

| Règle | Département (`customer-service/AGENTS.md`) | Sous-domaine (`returns/AGENTS.md`) | Ce qui s'applique |
|---|---|---|---|
| Validation d'un superviseur | au-dessus de 300 TND | **au-dessus de 200 TND** | 200 TND |
| Délai de retour | 14 jours | **7 jours pour l'électronique** | 7 jours pour un smartphone |

La requête `cs-01` (casque à 349 TND) vérifie que Gemini applique bien **200** et non 300.

### Le budget de tokens

Le contexte ne doit pas dépasser 6 000 tokens (réglable dans `.env`). Si c'est trop gros, le compilateur, dans cet ordre :
1. **masque** les anciennes sorties d'outils (dès 70 % du budget) : une sortie de 350 lignes devient `[sortie masquée : get_order, 350 lignes, 21000 tokens, id obs-0042]` ;
2. retire les **annexes**, la plus ancienne d'abord ;
3. désactive le **skill le plus ancien** (au maximum 2 skills actifs à la fois).

---

## 7. Étape C : l'IA utilise le skill, le code contrôle

Gemini ne peut répondre que par **une action en JSON** (format imposé, vérifié par Pydantic dans `bench/schemas.py`) :

```json
{"action": "activate_skill", "skill": "return-request"}
{"action": "load_reference", "skill": "return-request", "filename": "refund_policy.md"}
{"action": "call_tool", "tool": "get_order", "arguments_json": "{\"order_id\": \"CMD-2026-0457\"}"}
{"action": "answer", "text": "Decision: HOLD ... Skill used: return-request"}
```

Avant chaque appel d'outil, la **garde** (`engine/guard.py`) vérifie :

| Contrôle | Code de refus |
|---|---|
| un skill est-il actif ? | `skill_not_active` |
| l'outil est-il dans `allowed-tools` d'un skill actif ? | `tool_not_allowed` |
| les arguments respectent-ils la définition de `tools/*.yaml` ? | `bad_arguments` |
| outil d'écriture sans « je confirme » de l'utilisateur ? | `confirmation_required` |

Ensuite, **l'exécuteur** appelle la vraie fonction Python de l'outil (`erp/tools.py`), qui lit ou modifie la base de démonstration. À la fin, le **vérificateur** (`engine/verifier.py`) contrôle la réponse : dernière ligne « Skill used: … », pas d'e-mail ni d'IBAN en clair, ligne « Decision: » pour `return-request`.

> **L'IA propose, notre code décide.**

---

## 8. Exemple complet, pas à pas (requête `cs-01`, exécution réelle)

Question : « La cliente demande le remboursement de la commande CMD-2026-0457. Peut-on accepter ? »

| Appel | Gemini propose | Le code fait | Contexte avec compilateur | Sans compilateur |
|---|---|---|---|---|
| 1 | `activate_skill return-request` | le compilateur ajoute les règles + la procédure + 5 outils | 1 178 | 4 409 |
| 2 | `call_tool get_order` | garde : ok ; la base renvoie : casque, électronique, 349 TND, livré il y a 4 jours | 3 123 | 4 409 |
| 3 | `call_tool get_customer` | garde : ok ; cliente **gold** (+7 jours) | 3 347 | 4 633 |
| 4 | `call_tool get_refunds` | garde : ok ; aucun remboursement | 3 448 | 4 734 |
| 5 | `load_reference refund_policy.md` | le compilateur ajoute l'annexe | 3 513 | 4 799 |
| 6 | `answer` | le vérificateur contrôle la réponse | 3 947 | 4 799 |

Réponse de Gemini : **Decision: HOLD**, car le montant dépasse **200 TND** (règle du sous-domaine) : il faut un superviseur. Aucun remboursement n'est enregistré. Les 5 vérifications de `tasks/customer-service/cs-01.yaml` sont réussies.

*(Les chiffres « sans compilateur » de ce tableau ont été mesurés avant l'ajout des annexes au mode monolithique ; ils sont un peu plus élevés aujourd'hui.)*

---

## 9. Ajouter un nouveau skill (exercice pour l'équipe)

1. Créer `departments/customer-service/<sous-domaine>/skills/<nom>/SKILL.md` avec l'en-tête et la procédure.
2. Si un nouvel outil est nécessaire : écrire sa fonction dans `erp/tools.py`, l'ajouter au catalogue `TOOLS`, puis le décrire dans `tools/customer-service.yaml`.
3. `python manage.py index_skills` : lire le statut affiché (active, needs_review ou rejected).
4. Ajouter une requête prédéfinie dans `tasks/customer-service/` avec ses vérifications.
5. L'exécuter depuis l'interface web et regarder les tokens dans le tableau de bord.

Les départements Finance, RH, Inventaire et Conformité sont des **squelettes vides** prêts à recevoir leurs skills de la même façon (voir le README de chaque dossier).
