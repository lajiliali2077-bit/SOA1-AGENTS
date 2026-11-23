"""Vérificateur : contrôle la réponse finale de l'IA avec des règles simples (regex).

    1. la dernière ligne est « Skill used: <skill> » (ou « Skill used: none » sans skill) ;
    2. aucun IBAN et aucune adresse e-mail en clair ;
    3. pour return-request : une ligne « Decision: APPROVE, REJECT ou HOLD ».
"""

import re

IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+")
DECISION = re.compile(r"^\s*(?:Decision|Décision)\s*:\s*(\w+)", re.IGNORECASE | re.MULTILINE)
SKILL_LINE = re.compile(r"Skill used\s*:\s*(.+)", re.IGNORECASE)

DECISIONS = {"return-request": ["APPROVE", "REJECT", "HOLD"]}


def verify_answer(text: str, used_skills: list) -> list:
    """Retourne la liste des problèmes (liste vide = réponse conforme)."""
    problems = []

    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    last = SKILL_LINE.fullmatch(lines[-1]) if lines else None
    if last is None:
        problems.append("skill_line: la dernière ligne doit être « Skill used: ... »")
    else:
        named = last.group(1).strip()
        if named.lower() == "none" and used_skills:
            problems.append(f"skill_line: « none » alors que {used_skills} a été utilisé")
        if named.lower() != "none" and named not in used_skills:
            problems.append(f"skill_line: {named} n'a pas été activé")

    if IBAN.search(text):
        problems.append("iban: IBAN en clair dans la réponse")
    if EMAIL.search(text):
        problems.append("email: adresse e-mail en clair dans la réponse")

    for skill in used_skills:
        if skill in DECISIONS:
            found = DECISION.search(text)
            if found is None or found.group(1).upper() not in DECISIONS[skill]:
                problems.append(f"decision: ligne « Decision: » attendue parmi {DECISIONS[skill]}")
    return problems
