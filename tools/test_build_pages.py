from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.build_pages import PagesBuildError, _normalize_lists, assemble


class AssemblePagesTests(unittest.TestCase):
    def make_repository(self, root: Path, with_export: bool = True) -> None:
        (root / "skills" / "techniques").mkdir(parents=True)
        (root / "skills" / "future" / "nested").mkdir(parents=True)
        (root / "skills" / "pocs").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "SKILL.md").write_text("# Skill home\n", encoding="utf-8")
        (root / "README.md").write_text("# About\n", encoding="utf-8")
        (root / "docs" / "figures.md").write_text("# Figure rules\n", encoding="utf-8")
        (root / "skills" / "future" / "nested" / "new.md").write_text(
            "# Automatically discovered\n", encoding="utf-8"
        )
        (root / "skills" / "pocs" / "README.md").write_text(
            "# POC records\n", encoding="utf-8"
        )
        technique = root / "skills" / "techniques"
        (technique / "fabric.drawio").write_text("<mxfile/>", encoding="utf-8")
        (technique / "fabric.md").write_text(
            "[Figure 1 — Fabric](fabric.drawio)\n", encoding="utf-8"
        )
        if with_export:
            (technique / "_figures").mkdir()
            (technique / "_figures" / "fabric.svg").write_text(
                "<svg/>", encoding="utf-8"
            )

    def test_copies_recursive_content_and_rewrites_figure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            self.make_repository(root)

            diagrams, links, indexes = assemble(root, root / ".pages-build")

            docs = root / ".pages-build" / "docs"
            self.assertEqual((diagrams, links), (1, 1))
            self.assertGreaterEqual(indexes, 3)
            self.assertEqual((docs / "index.md").read_text(), "# Skill home\n")
            self.assertTrue((docs / "skills" / "future" / "nested" / "new.md").is_file())
            self.assertTrue((docs / "skills" / "future" / "index.md").is_file())
            self.assertFalse((docs / "skills" / "pocs" / "README.md").exists())
            self.assertEqual(
                (docs / "skills" / "pocs" / "index.md").read_text(),
                "# POC records\n",
            )
            published = (docs / "skills" / "techniques" / "fabric.md").read_text()
            self.assertIn("![_", published.replace("Figure 1 — Fabric", "_"))
            self.assertIn("_figures/fabric.svg", published)
            self.assertIn("[Editable draw.io source](fabric.drawio)", published)

    def test_ignores_drawio_examples_inside_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            self.make_repository(root)
            example = (
                "```markdown\n"
                "[Figure 99 — Example only](missing.drawio)\n"
                "```\n\n"
                "`[Figure 98 — Inline example](also-missing.drawio)`\n"
            )
            (root / "docs" / "figures.md").write_text(example, encoding="utf-8")

            assemble(root, root / ".pages-build")

            published = (root / ".pages-build" / "docs" / "docs" / "figures.md").read_text()
            self.assertEqual(published, example)

    def test_rejects_drawio_link_embedded_in_prose(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            self.make_repository(root)
            technique = root / "skills" / "techniques" / "fabric.md"
            technique.write_text(
                "See [Figure 1 — Fabric](fabric.drawio) for details.\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(PagesBuildError, "invalid draw.io figure reference"):
                assemble(root, root / ".pages-build")

    def test_fails_when_export_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            self.make_repository(root, with_export=False)

            with self.assertRaisesRegex(PagesBuildError, "missing SVG export"):
                assemble(root, root / ".pages-build")


class NormalizeListsTests(unittest.TestCase):
    def test_inserts_blank_line_before_list_after_paragraph(self) -> None:
        self.assertEqual(
            _normalize_lists("**If it fails**:\n- one\n- two\n"),
            "**If it fails**:\n\n- one\n- two\n",
        )

    def test_reindents_github_nesting_to_four_spaces(self) -> None:
        source = (
            "- **Configuration**: values\n"
            "  1. Step one\n"
            "     wrapped.\n"
            "\n"
            "     ```\n"
            "     bgp 65002\n"
            "      peer x\n"
            "     ```\n"
            "\n"
            "     After the code.\n"
            "  2. Step two\n"
            "- **Verification**: TC-01.\n"
        )
        expected = (
            "- **Configuration**: values\n"
            "    1. Step one\n"
            "        wrapped.\n"
            "\n"
            "        ```\n"
            "        bgp 65002\n"
            "         peer x\n"
            "        ```\n"
            "\n"
            "        After the code.\n"
            "\n"
            "    2. Step two\n"
            "\n"
            "- **Verification**: TC-01.\n"
        )
        self.assertEqual(_normalize_lists(source), expected)

    def test_keeps_tight_lists_tight_and_top_level_code_unchanged(self) -> None:
        source = "- a\n  wrapped\n- b\n\n```\n  - not a list\n```\n"
        self.assertEqual(
            _normalize_lists(source),
            "- a\n    wrapped\n- b\n\n```\n  - not a list\n```\n",
        )


if __name__ == "__main__":
    unittest.main()
