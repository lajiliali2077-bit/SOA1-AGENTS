"""Vérifications d'une tâche (section checks des fichiers tasks/*.yaml)."""

import re

from engine.verifier import DECISION, IBAN


def answer_of(turns, check) -> str:
    """Réponse du tour demandé, sinon celle du dernier tour."""
    if check.turn:
        return turns[check.turn - 1].answer if check.turn <= len(turns) else ""
    return turns[-1].answer


def steps_of(turns, check) -> list:
    """Étapes du tour demandé, sinon de tous les tours."""
    chosen = [turns[check.turn - 1]] if check.turn and check.turn <= len(turns) else turns
    return [step for turn in chosen for step in turn.steps]


def run_check(check, turns) -> tuple:
    """Retourne (réussi, explication)."""
    if check.check == "skill_activated":
        skills = [s.detail for s in steps_of(turns, check) if s.action == "activate_skill" and s.guard == ""]
        if check.skill == "none":
            return not skills, f"skills activés : {skills}"
        return check.skill in skills, f"skills activés : {skills}"

    if check.check == "decision_is":
        found = DECISION.search(answer_of(turns, check))
        decision = found.group(1).upper() if found else None
        return decision in check.values, f"décision : {decision}"

    if check.check in ("tool_called", "tool_not_called"):
        calls = [s for s in steps_of(turns, check)
                 if s.action == "call_tool" and s.guard == "ok" and s.detail == check.tool]
        if check.arguments:
            calls = [s for s in calls
                     if all(s.arguments.get(k) == v for k, v in check.arguments.items())]
        called = len(calls) > 0
        return (called if check.check == "tool_called" else not called), f"exécuté {len(calls)} fois"

    if check.check == "text_contains":
        return str(check.value).lower() in answer_of(turns, check).lower(), f"« {check.value} »"

    if check.check == "text_matches":
        return re.search(check.pattern, answer_of(turns, check)) is not None, f"motif {check.pattern}"

    if check.check == "iban_masked":
        return not any(IBAN.search(t.answer) for t in turns), "aucun IBAN en clair"

    if check.check == "context_compacted":
        compacted = any(s.compacted for s in steps_of(turns, check))
        return compacted == check.value, f"compacted = {compacted}"

    return False, "check inconnu"


def evaluate(task, turns) -> list:
    results = []
    for check in task.checks:
        passed, detail = run_check(check, turns)
        results.append({"check": check.check, "passed": passed, "detail": detail})
    return results
