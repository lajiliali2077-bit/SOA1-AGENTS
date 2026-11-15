"""Tests du parser SKILL.md."""

import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from registry.parser import SkillError, discover_skills, parse_skill_file

VALID = (
    "---\n"
    "name: demo-skill\n"
    "description: Demo skill. Use when testing the parser.\n"
    "allowed-tools: tool_a tool_b\n"
    "---\n\n"
    "# Demo\n\n1. Do something.\n"
)


class SkillParserTests(SimpleTestCase):
    def write_skill(self, content, dirname="demo-skill"):
        """Écrit un SKILL.md dans une arborescence temporaire departments/dept/sub/skills/<dirname>/."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name) / "departments" / "dept" / "sub" / "skills" / dirname
        folder.mkdir(parents=True)
        path = folder / "SKILL.md"
        path.write_text(content, encoding="utf-8", newline="")
        return path

    def test_valid_skill(self):
        skill = parse_skill_file(self.write_skill(VALID))
        self.assertEqual(skill.meta.name, "demo-skill")
        self.assertEqual(skill.meta.allowed_tools, ["tool_a", "tool_b"])
        self.assertEqual((skill.department, skill.subdomain), ("dept", "sub"))
        self.assertGreater(skill.body_tokens, 0)
        self.assertEqual(skill.warnings, [])

    def test_crlf_line_endings(self):
        skill = parse_skill_file(self.write_skill(VALID.replace("\n", "\r\n")))
        self.assertEqual(skill.meta.name, "demo-skill")

    def test_missing_frontmatter(self):
        with self.assertRaisesMessage(SkillError, "frontmatter absent"):
            parse_skill_file(self.write_skill("# No frontmatter\n"))

    def test_uppercase_name_rejected(self):
        content = VALID.replace("name: demo-skill", "name: Demo-Skill")
        with self.assertRaisesMessage(SkillError, "name"):
            parse_skill_file(self.write_skill(content))

    def test_double_hyphen_rejected(self):
        content = VALID.replace("name: demo-skill", "name: demo--skill")
        with self.assertRaisesMessage(SkillError, "name"):
            parse_skill_file(self.write_skill(content))

    def test_name_must_match_folder(self):
        with self.assertRaisesMessage(SkillError, "dossier"):
            parse_skill_file(self.write_skill(VALID, dirname="other-folder"))

    def test_missing_description_rejected(self):
        content = VALID.replace("description: Demo skill. Use when testing the parser.\n", "")
        with self.assertRaisesMessage(SkillError, "description"):
            parse_skill_file(self.write_skill(content))

    def test_unknown_field_rejected(self):
        content = VALID.replace("---\n\n#", "color: red\n---\n\n#")
        with self.assertRaisesMessage(SkillError, "color"):
            parse_skill_file(self.write_skill(content))

    def test_allowed_tools_must_be_a_string(self):
        content = VALID.replace("allowed-tools: tool_a tool_b", "allowed-tools: [tool_a, tool_b]")
        with self.assertRaisesMessage(SkillError, "allowed"):
            parse_skill_file(self.write_skill(content))

    def test_warning_without_use_when(self):
        content = VALID.replace("Demo skill. Use when testing the parser.", "Demo skill for testing.")
        skill = parse_skill_file(self.write_skill(content))
        self.assertEqual(len(skill.warnings), 1)

    def test_real_departments_are_valid(self):
        paths = discover_skills(settings.BASE_DIR / "departments")
        self.assertGreaterEqual(len(paths), 12)
        skills = [parse_skill_file(p) for p in paths]
        self.assertEqual(len({s.meta.name for s in skills}), len(skills))
        self.assertTrue({"finance", "hr", "inventory", "compliance"} <= {s.department for s in skills})