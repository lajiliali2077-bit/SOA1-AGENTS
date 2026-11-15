# Guide : enrichir un département

Finance est le **département de référence**. HR, Inventory et Compliance suivent le même modèle. Lisez les fichiers de `departments/finance/` avant d'écrire les vôtres.

## 1. Principe
Le copilote charge le contexte par couches (progressive disclosure) :
- **Niveau 1 de contexte** : `AGENTS.md` global, plus l'index des skills (nom + description).
- **Niveau 2** : `AGENTS.md` du département et du sous-domaine, puis le corps du `SKILL.md` activé.
- **Niveau 3** : fichiers `references/` et définitions d'outils, chargés seulement à la demande.

Les `AGENTS.md` sont assemblés dans l'ordre global, département, sous-domaine : **la règle la plus proche gagne**.

## 2. À livrer par département
- 3 `AGENTS.md` utiles : 1 de département et 1 par sous-domaine (2 sous-domaines).
- Les 3 skills existants, enrichis (ne pas en ajouter ni en retirer sans accord de l'équipe : un test attend 12 skills).
- Des fichiers `references/` pour chaque skill (schémas de données, politiques, glossaires, matrices).
- Le catalogue d'outils `tools/<département>.yaml` : 12 outils.
- **Au moins une règle surchargée** entre le niveau département et le niveau sous-domaine (comme le seuil de 5000 TND en Accounts-Payable).

## 3. Structure
```
departments/<dept>/AGENTS.md
departments/<dept>/<sous-domaine>/AGENTS.md
departments/<dept>/<sous-domaine>/skills/<nom-du-skill>/SKILL.md
departments/<dept>/<sous-domaine>/skills/<nom-du-skill>/references/*.md
tools/<dept>.yaml
```
Ne modifiez que votre département et votre fichier d'outils. Le `AGENTS.md` racine et le code (`registry/`) ne se changent qu'après discussion.

## 4. Règles pour un SKILL.md
- Le fichier commence par `---` à la première ligne, avec `name`, `description` et `allowed-tools`.
- `name` : minuscules, chiffres et tirets, **identique au nom du dossier** du skill.
- `description` : 1 à 1024 caractères, dit ce que fait le skill **et contient « Use when … »**. Entourez-la de guillemets si elle contient « : ».
- `allowed-tools` : une chaîne avec les noms séparés par des espaces (pas une liste YAML).
- Aucun autre champ n'est accepté par le parser.
- Corps recommandé : When to use, Procedure (étapes numérotées), Answer template, Example, Edge cases. Citez uniquement les outils déclarés dans `allowed-tools`.
- Renvoyez vers les fichiers de niveau 3 avec un chemin relatif, par exemple `references/invoice_schema.md`, sur un seul niveau de profondeur.

## 5. Règles pour un AGENTS.md
- Markdown simple, sans frontmatter. Sections courtes, règles en liste, chiffres précis (seuils, délais, formats).
- Indiquez dans le texte quand une règle en remplace une autre (« overrides the department threshold »).
- Pas de répétition d'une règle déjà présente à un niveau supérieur.

## 6. Catalogue d'outils
Modèle : `tools/finance.yaml`. Chaque outil a `name`, `description`, `mode` (`read` ou `write`), `departments` (départements autorisés) et `parameters`.
- Un outil partagé est défini **une seule fois**, dans le fichier du département propriétaire (exemple : `get_vendor` dans `finance.yaml`, avec `departments: [finance, inventory]`). Ne le redéfinissez pas.
- Compliance : tous les outils sont en lecture seule (`mode: read`).
- Les noms doivent correspondre exactement à ceux de `allowed-tools`.
- La validation automatique du catalogue sera ajoutée plus tard (incrément 7) : respectez le format dès maintenant.

## 7. Tailles visées (mesurées sur Finance)
| Élément | Finance | Cible |
|---|---|---|
| AGENTS.md de département | 450 | 350 à 550 |
| AGENTS.md de sous-domaine | 318 à 340 | 250 à 450 |
| SKILL.md (frontmatter + corps) | 396 à 718 | 400 à 750 (max 5000) |
| Fichier de référence | 230 à 584 | 250 à 600 |
| Définition d'un outil | environ 170 | 150 à 250 |
| **Département complet** | **6 554** | **environ 5 500 à 7 500** |

## 8. Vérifier avant de commiter
```powershell
python scripts\show_skills.py
python scripts\measure_dept.py <département>
python manage.py test registry
```
- `show_skills.py` doit afficher `0 erreurs` et aucun avertissement pour vos skills.
- `measure_dept.py` donne le détail en tokens fichier par fichier.
- Les tests doivent passer (`OK`).

## 9. Pièges courants
- Encodage : UTF-8 sans BOM (VS Code par défaut). Les fins de ligne CRLF de Windows sont acceptées.
- Un `:` suivi d'un espace dans une description non guillemetée casse le YAML.
- Un nom de skill identique à celui d'un autre département est refusé.
- Ne collez pas de commandes PowerShell dans un fichier de données.