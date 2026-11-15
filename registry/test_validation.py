"""Tests du catalogue d'outils et de la validation des skills."""

import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from registry.tools import load_catalog
from registry.validation import ACTIVE, NEEDS_REVIEW, REJECTED, validate_all

DEPARTMENTS = ("finance", "hr", "inventory", "compliance")


def tool_yaml(name, mode="read", departments=("hr",)):
    return (
        f"- name: {name}\n"
        f'  description: "Tool {name}."\n'
        f"  mode: {mode}\n"
        f"  departments: [{', '.join(departments)}]\n"
    )


def codes(report):
    return {issue.code for issue in report.issues}


class TempTreeTestCase(SimpleTestCase):
    """Fournit une arborescence temporaire departments/ et tools/."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "departments").mkdir()
        (self.root / "tools").mkdir()

    def add_tools(self, dept, text):
        (self.root / "tools" / f"{dept}.yaml").write_text(text, encoding="utf-8", newline="")

    def add_skill(self, dept, sub, name, tools, body=None):
        folder = self.root / "departments" / dept / sub / "skills" / name
        folder.mkdir(parents=True)
        if body is None:
            body = "Uses " + " ".join(tools) + "."
        content = (
            f"---\nname: {name}\n"
            "description: Demo skill. Use when testing.\n"
            f"allowed-tools: {' '.join(tools)}\n"
            f"---\n\n# {name}\n\n{body}\n"
        )
        (folder / "SKILL.md").write_text(content, encoding="utf-8", newline="")
        return folder

    def validate(self):
        return validate_all(self.root / "departments", self.root / "tools")

    def report(self, result, name):
        return next(r for r in result.reports if r.name == name)


class ValidationTests(TempTreeTestCase):
    def test_clean_skill_is_active(self):
        self.add_tools("hr", tool_yaml("get_thing"))
        self.add_skill("hr", "recruitment", "clean-skill", ["get_thing"])
        report = self.report(self.validate(), "clean-skill")
        self.assertEqual(report.status, ACTIVE)

    def test_unknown_tool_is_rejected(self):
        self.add_tools("hr", tool_yaml("get_thing"))
        self.add_skill("hr", "recruitment", "bad-skill", ["missing_tool"])
        report = self.report(self.validate(), "bad-skill")
        self.assertEqual(report.status, REJECTED)
        self.assertIn("E_TOOL_UNKNOWN", codes(report))

    def test_tool_of_another_department_is_rejected(self):
        self.add_tools("hr", tool_yaml("get_thing", departments=("hr",)))
        self.add_skill("finance", "treasury", "thief-skill", ["get_thing"])
        report = self.report(self.validate(), "thief-skill")
        self.assertEqual(report.status, REJECTED)
        self.assertIn("E_TOOL_FORBIDDEN", codes(report))

    def test_shared_tool_is_allowed_in_listed_departments(self):
        self.add_tools("hr", tool_yaml("get_thing", departments=("hr", "finance")))
        self.add_skill("finance", "treasury", "shared-skill", ["get_thing"])
        report = self.report(self.validate(), "shared-skill")
        self.assertEqual(report.status, ACTIVE)

    def test_write_tool_is_possible_in_every_department(self):
        for dept in DEPARTMENTS:
            self.add_tools(dept, tool_yaml(f"write_{dept}", mode="write", departments=(dept,)))
            self.add_skill(dept, "sub", f"{dept}-writer", [f"write_{dept}"])
        result = self.validate()
        for dept in DEPARTMENTS:
            with self.subTest(department=dept):
                report = self.report(result, f"{dept}-writer")
                self.assertEqual(report.status, NEEDS_REVIEW)
                self.assertIn("W_WRITE_TOOL", codes(report))

    def test_tool_cited_but_not_declared_gives_warning(self):
        self.add_tools("hr", tool_yaml("tool_a") + tool_yaml("tool_b"))
        self.add_skill("hr", "recruitment", "sneaky-skill", ["tool_a"], body="Use tool_a then tool_b.")
        report = self.report(self.validate(), "sneaky-skill")
        self.assertEqual(report.status, NEEDS_REVIEW)
        self.assertIn("W_TOOL_UNDECLARED", codes(report))

    def test_tool_declared_but_never_cited_gives_warning(self):
        self.add_tools("hr", tool_yaml("tool_a") + tool_yaml("tool_b"))
        self.add_skill("hr", "recruitment", "greedy-skill", ["tool_a", "tool_b"], body="Use tool_a only.")
        report = self.report(self.validate(), "greedy-skill")
        self.assertEqual(report.status, NEEDS_REVIEW)
        self.assertIn("W_TOOL_UNUSED", codes(report))

    def test_longer_tool_name_does_not_count_as_a_mention(self):
        self.add_tools("hr", tool_yaml("get_vendor"))
        self.add_skill("hr", "recruitment", "prefix-skill", ["get_vendor"], body="Use get_vendor_history.")
        report = self.report(self.validate(), "prefix-skill")
        self.assertIn("W_TOOL_UNUSED", codes(report))

    def test_missing_reference_gives_warning(self):
        self.add_tools("hr", tool_yaml("get_thing"))
        self.add_skill("hr", "recruitment", "ref-skill", ["get_thing"], body="Use get_thing. Read references/missing.md.")
        report = self.report(self.validate(), "ref-skill")
        self.assertEqual(report.status, NEEDS_REVIEW)
        self.assertIn("W_REFERENCE_MISSING", codes(report))

    def test_existing_reference_is_fine_and_unused_one_is_only_info(self):
        self.add_tools("hr", tool_yaml("get_thing"))
        folder = self.add_skill("hr", "recruitment", "refs-skill", ["get_thing"], body="Use get_thing. Read references/guide.md.")
        (folder / "references").mkdir()
        (folder / "references" / "guide.md").write_text("# Guide\n", encoding="utf-8")
        (folder / "references" / "notes.md").write_text("# Notes\n", encoding="utf-8")
        report = self.report(self.validate(), "refs-skill")
        self.assertEqual(report.status, ACTIVE)
        self.assertNotIn("W_REFERENCE_MISSING", codes(report))
        self.assertIn("I_REFERENCE_UNUSED", codes(report))

    def test_duplicate_skill_names_are_rejected(self):
        self.add_tools("hr", tool_yaml("get_thing"))
        self.add_skill("hr", "recruitment", "same-name", ["get_thing"])
        self.add_skill("hr", "payroll", "same-name", ["get_thing"])
        reports = [r for r in self.validate().reports if r.name == "same-name"]
        self.assertEqual(len(reports), 2)
        for report in reports:
            self.assertEqual(report.status, REJECTED)
            self.assertIn("E_DUPLICATE_NAME", codes(report))

    def test_parse_error_is_reported_as_rejected(self):
        folder = self.root / "departments" / "hr" / "recruitment" / "skills" / "broken-skill"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
        report = self.report(self.validate(), "broken-skill")
        self.assertEqual(report.status, REJECTED)
        self.assertIn("E_PARSE", codes(report))


class CatalogTests(TempTreeTestCase):
    def load(self):
        return load_catalog(self.root / "tools", {"hr", "finance"})

    def test_valid_catalog(self):
        self.add_tools("hr", tool_yaml("tool_a"))
        catalog = self.load()
        self.assertEqual(catalog.errors, [])
        self.assertIn("tool_a", catalog.tools)

    def test_tool_defined_twice_is_an_error(self):
        self.add_tools("finance", tool_yaml("tool_x", departments=("finance",)))
        self.add_tools("hr", tool_yaml("tool_x", departments=("hr",)))
        self.assertTrue(any("déjà défini" in e for e in self.load().errors))

    def test_owner_must_be_listed_in_departments(self):
        self.add_tools("hr", tool_yaml("tool_x", departments=("finance",)))
        self.assertTrue(any("propriétaire" in e for e in self.load().errors))

    def test_invalid_mode_is_an_error(self):
        self.add_tools("hr", '- name: tool_x\n  description: "x"\n  mode: delete\n  departments: [hr]\n')
        self.assertTrue(any("mode" in e for e in self.load().errors))

    def test_unknown_department_is_an_error(self):
        self.add_tools("hr", tool_yaml("tool_x", departments=("hr", "nowhere")))
        self.assertTrue(any("inconnus" in e for e in self.load().errors))

    def test_file_name_must_match_a_department(self):
        self.add_tools("ghost", tool_yaml("tool_x", departments=("ghost",)))
        self.assertTrue(any("aucun département" in e for e in self.load().errors))


class RealCorpusTests(SimpleTestCase):
    def test_real_corpus_has_no_rejected_skill_and_no_catalog_error(self):
        result = validate_all(settings.BASE_DIR / "departments", settings.BASE_DIR / "tools")
        self.assertEqual(result.catalog.errors, [])
        self.assertEqual([r.name for r in result.reports if r.status == REJECTED], [])
        self.assertGreaterEqual(len(result.reports), 12)