# Département RH : squelette d'extension (vide pour l'instant)

Ce département n'est pas encore fonctionnel. Seul le département **Service client** (customer-service) l'est.
Les dossiers sont prêts : pour l'activer, suivre le modèle de `departments/customer-service/`.

## Étapes pour l'activer
1. Écrire `departments/hr/AGENTS.md` : les règles du département (niveau 2).
2. Pour chaque sous-domaine (payroll, recruitment) : écrire `AGENTS.md` (niveau 3).
3. Pour chaque compétence : créer `<sous-domaine>/skills/<nom-du-skill>/SKILL.md`
   (en-tête `name`, `description` avec « Use when... », `allowed-tools`, puis la procédure).
4. Écrire les fonctions Python des outils dans `erp/tools.py` et les ajouter au catalogue `TOOLS`.
5. Décrire ces outils pour l'IA dans `tools/hr.yaml` (nom, description, mode read/write, paramètres).
6. Ajouter des requêtes prédéfinies dans `tasks/hr/`.
7. Lancer `python manage.py index_skills` : le registre vérifie et enregistre le tout.

Explication détaillée : `docs/SKILLS.md`.
