"""Tests de l'indexeur du registre (base PostgreSQL de test)."""

import shutil
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from registry.indexer import index_all
from registry.models import AgentsFile, Skill, Tool
from registry.validation import ACTIVE, NEEDS_REVIEW


def tool_yaml(name, mode="read", departments=("hr",)):
    return (
        f"- name: {name}\n"
        f'  description: "Tool {name}."\n'
        f"  mode: {mode}\n"
        f"  departments: [{', '.join(departments)}]\n"
    )


class IndexerTests(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()  # resolve : évite les chemins courts de Windows
        (self.root / "departments").mkdir()
        (self.root / "tools").mkdir()
        override = override_settings(BASE_DIR=self.root)
        override.enable()
        self.addCleanup(override.disable)

    # ---- aides ----
    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def add_tools(self, dept, text):
        self.write(f"tools/{dept}.yaml", text)

    def add_skill(self, dept, sub, name, tools, body=None):
        if body is None:
            body = "Uses " + " ".join(tools) + "."
        self.write(
            f"departments/{dept}/{sub}/skills/{name}/SKILL.md",
            f"---\nname: {name}\ndescription: Demo skill. Use when testing.\n"
            f"allowed-tools: {' '.join(tools)}\n---\n\n# {name}\n\n{body}\n",
        )

    def build_tree(self):
        """2 outils, 2 skills (un actif, un à valider), 3 AGENTS.md (un par niveau)."""
        self.add_tools("hr", tool_yaml("get_thing") + tool_yaml("set_thing", mode="write"))
        self.add_skill("hr", "recruitment", "clean-skill", ["get_thing"])
        self.add_skill("hr", "recruitment", "writer-skill", ["set_thing"])
        self.write("AGENTS.md", "# Global\n\nRule one.\n")
        self.write("departments/hr/AGENTS.md", "# HR\n\nRule two.\n")
        self.write("departments/hr/recruitment/AGENTS.md", "# Recruitment\n\nRule three.\n")

    def counts(self):
        return Tool.objects.count(), Skill.objects.count(), AgentsFile.objects.count()

    # ---- tests ----
    def test_first_run_creates_everything(self):
        self.build_tree()
        report = index_all()
        self.assertTrue(report.written)
        self.assertEqual(self.counts(), (2, 2, 3))
        self.assertEqual(report.created["skills"], 2)
        self.assertEqual(Skill.objects.get(name="clean-skill").status, ACTIVE)
        writer = Skill.objects.get(name="writer-skill")
        self.assertEqual(writer.status, NEEDS_REVIEW)
        self.assertIn("W_WRITE_TOOL", [issue["code"] for issue in writer.issues])
        self.assertEqual(sorted(AgentsFile.objects.values_list("level", flat=True)), [1, 2, 3])

    def test_second_run_creates_nothing(self):
        self.build_tree()
        index_all()
        second = index_all()
        self.assertEqual(sum(second.created.values()), 0)
        self.assertEqual(second.refreshed["skills"], 2)
        self.assertEqual(self.counts(), (2, 2, 3))

    def test_modified_skill_is_refreshed(self):
        self.build_tree()
        index_all()
        self.add_skill("hr", "recruitment", "clean-skill", ["get_thing"], body="Uses get_thing. New instruction.")
        index_all()
        self.assertIn("New instruction", Skill.objects.get(name="clean-skill").body)
        self.assertEqual(Skill.objects.count(), 2)

    def test_rejected_skill_is_excluded_but_others_are_indexed(self):
        self.build_tree()
        self.add_skill("hr", "recruitment", "bad-skill", ["missing_tool"])
        report = index_all()
        self.assertTrue(report.written)
        self.assertEqual([r.name for r in report.rejected], ["bad-skill"])
        self.assertFalse(Skill.objects.filter(name="bad-skill").exists())
        self.assertEqual(Skill.objects.count(), 2)

    def test_skill_that_becomes_invalid_is_removed(self):
        self.build_tree()
        index_all()
        self.assertTrue(Skill.objects.filter(name="clean-skill").exists())
        self.add_skill("hr", "recruitment", "clean-skill", ["missing_tool"])
        report = index_all()
        self.assertEqual(report.removed["skills"], 1)
        self.assertFalse(Skill.objects.filter(name="clean-skill").exists())

    def test_deleted_files_are_removed(self):
        self.build_tree()
        index_all()
        shutil.rmtree(self.root / "departments/hr/recruitment/skills/writer-skill")
        (self.root / "departments/hr/recruitment/AGENTS.md").unlink()
        report = index_all()
        self.assertEqual(report.removed["skills"], 1)
        self.assertEqual(report.removed["agents"], 1)
        self.assertEqual(self.counts(), (2, 1, 2))

    def test_invalid_catalog_writes_nothing(self):
        self.add_tools("hr", '- name: bad_tool\n  description: "x"\n  mode: delete\n  departments: [hr]\n')
        self.add_skill("hr", "recruitment", "some-skill", ["bad_tool"])
        report = index_all()
        self.assertTrue(report.catalog_errors)
        self.assertFalse(report.written)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_broken_catalog_keeps_existing_rows(self):
        self.build_tree()
        index_all()
        self.add_tools("hr", "not: a list\n")
        report = index_all()
        self.assertTrue(report.catalog_errors)
        self.assertFalse(report.written)
        self.assertEqual(self.counts(), (2, 2, 3))

    def test_paths_are_relative_with_slashes(self):
        self.build_tree()
        index_all()
        self.assertEqual(
            Skill.objects.get(name="clean-skill").path,
            "departments/hr/recruitment/skills/clean-skill/SKILL.md",
        )
        self.assertEqual(
            set(AgentsFile.objects.values_list("path", flat=True)),
            {"AGENTS.md", "departments/hr/AGENTS.md", "departments/hr/recruitment/AGENTS.md"},
        )

    def test_tool_owner_departments_and_tokens(self):
        # Les départements connus sont les dossiers de departments/ : on crée hr et finance.
        self.write("departments/hr/AGENTS.md", "# HR\n")
        self.write("departments/finance/AGENTS.md", "# Finance\n")
        self.add_tools("hr", tool_yaml("shared_tool", departments=("hr", "finance")))
        report = index_all()
        self.assertEqual(report.catalog_errors, [])
        tool = Tool.objects.get(name="shared_tool")
        self.assertEqual(tool.owner, "hr")
        self.assertEqual(tool.departments, ["hr", "finance"])
        self.assertEqual(tool.mode, "read")
        self.assertGreater(tool.tokens, 0)


class RealCorpusIndexTests(TestCase):
    def test_real_corpus_indexes_without_rejection(self):
        report = index_all()
        self.assertEqual(report.catalog_errors, [])
        self.assertEqual([r.name for r in report.rejected], [])
        self.assertTrue(report.written)
        self.assertGreaterEqual(Skill.objects.count(), 12)
        self.assertGreaterEqual(Tool.objects.count(), 21)
        self.assertGreaterEqual(AgentsFile.objects.count(), 13)
        self.assertEqual(AgentsFile.objects.filter(level=1).count(), 1)