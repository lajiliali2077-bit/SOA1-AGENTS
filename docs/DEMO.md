# Démo de la soutenance : avec Gemini, ou plan B hors ligne

## Avant la soutenance (une seule fois)

```powershell
docker compose up -d db
python manage.py migrate
python manage.py index_skills
python manage.py benchmark          # remplit docs/BENCHMARK.md et le tableau de bord
```

## Plan A : avec la vraie IA (Gemini Flash)

1. Créer une clé sur https://aistudio.google.com/apikey.
2. Copier `.env.example` en `.env`, puis remplir `GEMINI_API_KEY=...`. Ne jamais commiter `.env`.
3. Tester la connexion (un seul appel) :
   ```powershell
   python manage.py check_gemini
   ```
   Le message attendu est `Connexion OK. Action reçue : answer`. Si le modèle n'existe plus, changer `GEMINI_MODEL` dans `.env` (voir la liste des modèles dans Google AI Studio).
4. Lancer une tâche avec Gemini :
   ```powershell
   python manage.py run_task fin-01 --client gemini
   python manage.py demo --client gemini
   ```
5. Poser une question libre par l'API (serveur lancé avec `python manage.py runserver`) :
   ```powershell
   Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/run/ -ContentType "application/json" -Body '{"message": "Peux-tu approuver la facture INV-2026-00457 ?"}'
   ```

Une vraie IA ne répond pas toujours pareil : une tâche peut échouer à un check. C'est normal, et c'est justement ce que le moteur déterministe détecte et signale.

## Plan B : sans Internet ni clé (contingence)

```powershell
python manage.py demo
```

- Le client `scripted` rejoue des actions écrites à l'avance (`bench/scripted/finance.yaml`). **Ce n'est pas une IA**, et il faut le dire au jury.
- Tout le reste est réel : compilateur, budget, masquage, garde, exécuteur, vérificateur, checks, base PostgreSQL, tableau de bord.
- Avec `--client auto` (le défaut de `run_task`), Gemini est utilisé si une clé est présente, sinon le plan B.

## Les 3 scénarios de `demo`

| Tâche | Ce qu'on montre | Ce qu'il faut regarder |
|---|---|---|
| fin-01 | Règle surchargée : le sous-domaine (5000 TND) remplace le département (10000 TND) | « Decision: HOLD », approbation par un manager |
| fin-02 | La garde refuse l'écriture sans confirmation | `[garde : confirmation_required]` au tour 1, `[garde : ok]` au tour 2 |
| fin-07 | Sortie d'outil énorme (350 lignes) | le check `context_compacted` est OK : les anciennes sorties sont masquées |

Ensuite : ouvrir http://127.0.0.1:8000/dashboard/ pour la comparaison des tokens.

## Montrer la synchronisation (webhook signé)

```powershell
$env:GITHUB_WEBHOOK_SECRET = "demo-secret"     # dans le même terminal que runserver
python manage.py runserver
```
Dans un second terminal :
```powershell
$body = '{"ref":"refs/heads/main","after":"abc1234"}'
$hmac = New-Object System.Security.Cryptography.HMACSHA256 (,[Text.Encoding]::UTF8.GetBytes("demo-secret"))
$sig = "sha256=" + (($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($body)) | % { $_.ToString("x2") }) -join "")
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/sync/github/ -Body $body -ContentType "application/json" -Headers @{"X-GitHub-Event"="push"; "X-Hub-Signature-256"=$sig}
```
Le statut doit être `ok`. Avec une fausse signature, la réponse est une erreur 403. La synchronisation apparaît ensuite sur le tableau de bord.

Avec n8n : `docker compose up -d n8n`, ouvrir http://localhost:5678, importer `n8n/github_sync_workflow.json`, puis mettre la même valeur dans `N8N_SYNC_TOKEN` (fichier `.env` et environnement de n8n).
