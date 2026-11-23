# Benchmark : mode progressif contre mode monolithique

Commande : `python manage.py benchmark --client scripted`. Budget : 6000 tokens. Tokens comptés avec tiktoken (estimation).

Avec le client `scripted`, les actions de l'agent sont écrites à l'avance (bench/scripted/finance.yaml) : les deux modes reçoivent exactement les mêmes actions.

Contexte au démarrage : 999 tokens (progressif) contre 7236 tokens (monolithique), soit 86.2 % de moins.

| tâche | piège | appels IA | pic progressif | pic monolithique | total progressif | total monolithique | économie | checks progressif | checks monolithique |
|---|---|---|---|---|---|---|---|---|---|
| fin-01 | none | 7 | 4185 | 7753 | 23805 | 52965 | 55.1 % | réussi | réussi |
| fin-02 | write_without_confirmation | 9 | 4095 | 7966 | 31761 | 68966 | 53.9 % | réussi | réussi |
| fin-03 | none | 4 | 2846 | 7576 | 9013 | 29440 | 69.4 % | réussi | réussi |
| fin-04 | none | 10 | 4212 | 8319 | 32853 | 76430 | 57.0 % | réussi | réussi |
| fin-05 | out_of_scope | 1 | 1019 | 7256 | 1019 | 7256 | 86.0 % | réussi | réussi |
| fin-06 | injection | 6 | 3904 | 7775 | 19704 | 45296 | 56.5 % | réussi | réussi |
| fin-07 | large_output | 6 | 25712 | 29731 | 62908 | 132992 | 52.7 % | réussi | échec |

**Total : 181063 tokens (progressif) contre 413345 tokens (monolithique), soit 56.2 % de moins.**

Total = somme des contextes envoyés au modèle pendant la tâche. Pic = plus grand contexte envoyé en une fois.
