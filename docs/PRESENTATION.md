# Plan détaillé de la présentation (PowerPoint)

Ce plan suit le `README.md` : chaque diapositive renvoie à la section du README où se trouve le contenu. Une idée par diapositive, peu de texte, un visuel à chaque fois.

- **Durée visée** : environ 20 minutes (15 min de diapositives + 5 min de démo en direct), puis les questions.
- **Répartition** : 5 orateurs, environ 4 minutes chacun. Chaque membre doit pourtant savoir expliquer le compilateur, la garde et le webhook (README §14).
- **Visuels à préparer** : voir README §12 (diagrammes exportés depuis mermaid.live ou redessinés dans draw.io, graphique Excel depuis `docs/benchmark.csv`, captures d'écran).

---

## Partie 1 : le problème et l'idée (orateur 1, ~4 min)

### Diapositive 1 : Titre
- Nom du projet : *SOA1-AGENTS, le Progressive Context Compiler*
- Matière SOA, noms des 5 membres, date
- **Visuel** : logo de l'école, éventuellement le schéma d'architecture en petit

### Diapositive 2 : Le problème
- Une IA lit un **contexte** avant de répondre, et ce contexte a une taille limitée (en **tokens**).
- Trop de texte : **plus cher, plus lent, moins précis** (*context rot*, *lost in the middle*).
- **Visuel** : une pile de 3 000 pages face à une seule fiche
- **À dire** : « Donner 3 000 pages à un nouvel employé le premier jour, c'est la mauvaise méthode. »
- **Source** : README §1 ; COMPARAISON.md [3][4]

### Diapositive 3 : Notre idée
- Donner à l'IA **seulement ce qui est utile, au bon moment** : le sommaire, puis le chapitre, puis l'annexe.
- L'IA **propose**, notre code **décide** (moteur déterministe).
- Le résultat en une ligne : **56 % de tokens en moins**, 7 tâches sur 7 réussies.
- **Visuel** : 3 marches (niveau 1, 2, 3)
- **Source** : README §1

### Diapositive 4 : Définitions formelles (1/2)
- Contexte, token, tiktoken, AGENTS.md, AGENTS.md hiérarchique, SKILL.md
- Une phrase par notion, avec un exemple tiré du projet
- **Visuel** : tableau à 3 colonnes (notion, définition, exemple)
- **Source** : README §2 (lignes 1 à 7 du tableau)

### Diapositive 5 : Définitions formelles (2/2)
- Divulgation progressive, outil, observation, masquage, budget de tokens, moteur déterministe, Pydantic, webhook, signature HMAC, n8n, SOA
- **Visuel** : même tableau
- **Source** : README §2 (fin du tableau)

---

## Partie 2 : le contenu donné à l'IA (orateur 2, ~4 min)

### Diapositive 6 : AGENTS.md hiérarchique
- 3 niveaux : global, département, sous-domaine (13 fichiers)
- **Exemple** : Finance dit « Any operation above 10000 TND requires manager approval », Comptes fournisseurs dit « Invoices above 5000 TND require manager approval. This overrides... ». **Le plus proche gagne.**
- **Visuel** : arborescence `AGENTS.md`, `departments/finance/AGENTS.md`, `accounts-payable/AGENTS.md`, avec les deux phrases surlignées
- **Source** : README §2, §6 étape 1

### Diapositive 7 : Un SKILL.md
- En-tête : `name`, `description` (avec « Use when »), `allowed-tools`
- Corps : la procédure étape par étape ; dossier `references/` pour les annexes
- 12 skills, dont 3 en Finance (`invoice-validation`, `vendor-check`, `cash-forecast`)
- **Visuel** : capture du début de `invoice-validation/SKILL.md`
- **Source** : README §4 ; spécification agentskills.io (COMPARAISON.md [2])

### Diapositive 8 : Le registre et la validation
- `index_skills` lit les fichiers, vérifie avec Pydantic et enregistre dans PostgreSQL
- Rejeté : outil inconnu ou interdit au département. À valider : outil d'écriture, pas de « Use when »...
- Résultat : 12 skills (10 active, 2 needs_review, 0 rejected), 21 outils ; Finance = 6 444 tokens
- **Visuel** : capture de la sortie de `python manage.py index_skills`
- **Source** : README §5.2, §6 étape 2

---

## Partie 3 : l'architecture et le compilateur (orateur 3, ~4 min)

### Diapositive 9 : Architecture SOA
- 6 services, chacun dans une app Django : registre, compilateur, masquage, moteur, synchronisation, agent
- PostgreSQL = service de stockage ; API JSON entre l'extérieur et les services
- **Visuel** : le schéma d'architecture (README §3.2), exporté ou redessiné
- **À dire** : « Chaque service a un seul rôle et peut être testé seul. »
- **Source** : README §3.1, §3.2

### Diapositive 10 : Les 3 niveaux sur un exemple réel
- Question : « Peux-tu approuver la facture INV-2026-00457 ? »
- Départ ~1 000 tokens → skill activé ~3 400 → après les outils ~3 900 → après l'annexe ~4 200
- Sans compilateur : ~7 200 tokens **avant même la question**
- **Visuel** : histogramme en escalier, avec une barre rouge pour le monolithique
- **Source** : README §3.3

### Diapositive 11 : Le budget de tokens et le masquage
- Budget : 6 000 tokens par appel
- Ordre : 1) masquer les anciennes sorties dès 70 %, 2) retirer les annexes, 3) désactiver le skill le plus ancien. 2 skills actifs au maximum.
- Exemple de masquage : 350 lignes deviennent `[sortie masquée : get_invoice, 350 lignes, ... id obs-0007]` ; le texte complet reste en base
- **Visuel** : avant/après d'un bloc masqué
- **Source** : README §3.4

---

## Partie 4 : l'IA encadrée et l'automatisation (orateur 4, ~4 min)

### Diapositive 12 : Un tour de l'agent
- compile_context → IA → Pydantic → garde → exécuteur → vérificateur, jusqu'à la réponse finale
- L'IA ne peut répondre qu'avec 4 actions JSON
- **Visuel** : diagramme de séquence « un tour de l'agent » (docs/ARCHITECTURE.md §5)
- **Source** : README §3.5

### Diapositive 13 : Le moteur déterministe
- Tableau des contrôles : format (Pydantic), skill actif, outil autorisé, arguments, confirmation d'écriture, réponse finale (Skill used, IBAN, décision)
- **Exemple** : fin-02, l'écriture est refusée (`confirmation_required`), puis acceptée après « je confirme »
- **Visuel** : diagramme de séquence « écriture refusée » (docs/ARCHITECTURE.md §5) + tableau
- **À dire** : « L'IA propose, le code décide. »
- **Source** : README §3.6

### Diapositive 14 : Gemini, plan A et plan B
- Plan A : vraie IA Gemini Flash, réponse JSON imposée, test avec `check_gemini`
- Plan B : client `scripted` hors ligne, des actions rejouées (**pas une IA**), pour des tests reproductibles et une démo sans Internet
- **Visuel** : deux colonnes
- **Source** : README §3.7, §5.4

### Diapositive 15 : Synchronisation automatique
- push GitHub → webhook signé HMAC → Django vérifie (sinon 403) → `index_all()` → base à jour
- Variante visuelle : GitHub → n8n → Django (jeton secret)
- **Visuel** : diagramme de séquence de la synchronisation + capture du workflow n8n
- **Source** : README §3.8

---

## Partie 5 : preuves, démo et conclusion (orateur 5, ~4 min + démo)

### Diapositive 16 : Installation pas à pas
- Prérequis : Git, Python 3.14, Docker Desktop
- Les commandes, de `git clone` à `index_skills`
- **Visuel** : bloc de commandes (police à chasse fixe)
- **Source** : README §5.1, §5.2

### Diapositive 17 : Les commandes CLI
- `index_skills`, `run_task`, `demo`, `benchmark`, `check_gemini`, `runserver`, `pytest`, `docker compose`
- **Visuel** : tableau commande et rôle
- **Source** : README §9

### Diapositive 18 : Résultats chiffrés
- Démarrage : 999 contre 7 236 tokens (**−86 %**)
- 7 tâches : 181 063 contre 413 345 tokens (**−56 %**)
- Vérifications réussies : 7/7 en progressif, 6/7 en monolithique (échec sur la facture de 350 lignes)
- **Visuel** : graphique en barres par tâche (Excel, depuis `docs/benchmark.csv`)
- **Source** : README §7

### Diapositive 19 : Les pièges testés
- fin-01 règle surchargée, fin-02 écriture sans confirmation, fin-05 hors périmètre, fin-06 injection dans une facture, fin-07 sortie énorme
- 36 tests pytest + vérifications automatiques dans chaque tâche
- **Visuel** : tableau tâche, piège, résultat + capture « 36 passed »
- **Source** : README §7, §8

### Diapositive 20 : Matrice de comparaison
- 3 matrices : façon de donner la doc à l'IA, outil d'automatisation, outil de vérification
- Notes de 1 à 3, notre choix surligné, sources numérotées
- **Visuel** : les 3 tableaux (une diapositive chacun si c'est trop chargé)
- **Source** : docs/COMPARAISON.md

### Diapositive 21 : Démo en direct (~5 min)
- Suivre exactement le script du README §6 : `index_skills`, `demo`, tableau de bord, webhook 200 puis 403, `pytest`
- Plan B si problème : README §6, « Plan B si quelque chose ne marche pas »
- **Visuel** : une seule diapositive « Démo », puis basculer sur le terminal

### Diapositive 22 : Limites
- Tokens estimés avec tiktoken (pas le tokenizer de Gemini) ; outils simulés ; un seul département complet ; plan B qui n'est pas une IA ; API en Django simple
- **Source** : README §11

### Diapositive 23 : Conclusion
- Le compilateur donne le bon contexte au bon moment : **−56 % de tokens**, avec 7 tâches sur 7 réussies
- L'IA est encadrée par du code testé (36 tests)
- La documentation se met à jour seule (webhook / n8n)
- Merci, questions ?

---

## Diapositives de secours (après la conclusion, pour les questions)

- Les 8 questions du jury et leurs réponses (README §14)
- Captures d'écran de la démo, si la démo en direct a échoué (README §12)
- Correspondance énoncé et réalisation (README §10)

## Phrases simples pour l'oral

- « Le compilateur, c'est le bibliothécaire : il ne donne à l'IA que le livre et la page dont elle a besoin. »
- « L'IA propose, le code décide : chaque action passe par la garde avant d'être exécutée. »
- « Une sortie de 350 lignes devient une ligne : le texte complet reste en base, on peut le relire avec son identifiant. »
- « Si GitHub change un skill, le webhook met la base à jour ; une fausse signature est refusée. »
- « Mêmes actions, deux façons de construire le contexte : 56 % de tokens en moins. »
