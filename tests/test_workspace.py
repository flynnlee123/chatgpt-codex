import tempfile
import unittest
from pathlib import Path

from chatgpt_codex.workspace import WorkspaceTools


class WorkspaceToolsTests(unittest.TestCase):
    def test_lists_files_with_relative_paths(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "notes").mkdir()
            (root / "notes" / "a.txt").write_text("hello", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "ignored").write_text("secret", encoding="utf-8")

            result = WorkspaceTools(root).list_files(".", recursive=True, max_results=20)

            paths = [entry["path"] for entry in result["entries"]]
            self.assertIn("notes", paths)
            self.assertIn("notes/a.txt", paths)
            self.assertNotIn(".git/ignored", paths)
            self.assertFalse(result["truncated"])

    def test_reads_writes_and_searches_text(self):
        with tempfile.TemporaryDirectory() as workspace:
            tools = WorkspaceTools(Path(workspace))

            write_result = tools.write_file("src/app.py", "print('hello')\n")
            read_result = tools.read_file("src/app.py")
            search_result = tools.search_text("hello", path=".")

            self.assertEqual(write_result["bytes_written"], len("print('hello')\n".encode("utf-8")))
            self.assertEqual(read_result["content"], "print('hello')\n")
            self.assertEqual(search_result["matches"][0]["path"], "src/app.py")
            self.assertEqual(search_result["matches"][0]["line"], 1)

    def test_read_file_supports_line_ranges_and_line_numbers(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            target = root / "source.ts"
            target.write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

            result = WorkspaceTools(root).read_file(
                "source.ts",
                start_line=2,
                end_line=3,
                line_numbers=True,
            )

            self.assertEqual(result["content"], "2 | two\n3 | three\n")
            self.assertEqual(result["size_bytes"], target.stat().st_size)
            self.assertEqual(result["returned_bytes"], len(result["content"].encode("utf-8")))
            self.assertEqual(result["start_line"], 2)
            self.assertEqual(result["end_line"], 3)
            self.assertFalse(result["truncated"])

    def test_read_files_keeps_partial_results_and_applies_total_budget(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "a.txt").write_text("aaaa\n", encoding="utf-8")
            (root / "b.txt").write_text("bbbb\n", encoding="utf-8")
            result = WorkspaceTools(root).read_files(
                [{"path": "a.txt"}, {"path": "missing.txt"}, {"path": "b.txt"}],
                max_bytes_per_file=100,
                max_total_bytes=6,
            )

            self.assertEqual([item["path"] for item in result["files"]], ["a.txt", "missing.txt", "b.txt"])
            self.assertEqual(result["files"][0]["content"], "aaaa\n")
            self.assertEqual(result["files"][1]["error"]["code"], "file_not_found")
            self.assertEqual(result["files"][2]["content"], "b")
            self.assertTrue(result["files"][2]["truncated"])
            self.assertEqual(result["files"][2]["truncation_reason"], "max_total_bytes")
            self.assertEqual(result["total_returned_bytes"], 6)
            self.assertTrue(result["truncated"])
            self.assertEqual(result["truncation_reason"], "max_total_bytes")

    def test_list_files_supports_depth_and_glob_filters(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "src" / "nested").mkdir(parents=True)
            (root / "src" / "app.ts").write_text("app", encoding="utf-8")
            (root / "src" / "nested" / "deep.ts").write_text("deep", encoding="utf-8")
            (root / "notes.txt").write_text("notes", encoding="utf-8")

            default_listing = WorkspaceTools(root).list_files(".")
            self.assertEqual([entry["path"] for entry in default_listing["entries"]], ["notes.txt", "src"])

            shallow = WorkspaceTools(root).list_files(".", recursive=True, max_depth=1)
            self.assertEqual([entry["path"] for entry in shallow["entries"]], ["notes.txt", "src"])
            self.assertEqual([entry["depth"] for entry in shallow["entries"]], [1, 1])

            filtered = WorkspaceTools(root).list_files(
                ".",
                recursive=True,
                max_depth=3,
                include=["**/*.ts"],
                exclude=["src/nested/**"],
            )
            self.assertEqual([entry["path"] for entry in filtered["entries"]], ["src/app.ts"])

    def test_search_text_supports_case_insensitive_context_and_output_metadata(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "src").mkdir()
            (root / "src" / "app.ts").write_text("before\nNeedle value\nafter\n", encoding="utf-8")
            (root / "notes.txt").write_text("Needle outside include\n", encoding="utf-8")

            result = WorkspaceTools(root).search_text(
                "needle",
                case_sensitive=False,
                include=["**/*.ts"],
                context_before=1,
                context_after=1,
            )

            self.assertEqual(result["total_matches"], 1)
            self.assertEqual(result["returned_matches"], 1)
            match = result["matches"][0]
            self.assertEqual(match["line_text"], "Needle value")
            self.assertEqual(match["matched_text"], "Needle")
            self.assertEqual([line["line"] for line in match["context"]], [1, 2, 3])
            self.assertTrue(match["context"][1]["is_match"])
            self.assertFalse(result["truncated"])

    def test_apply_patch_updates_file(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "README.md").write_text("old title\nbody\n", encoding="utf-8")
            tools = WorkspaceTools(root)

            result = tools.apply_patch(
                """*** Begin Patch
*** Update File: README.md
@@
-old title
+new title
 body
*** End Patch
"""
            )

            self.assertEqual(result["changed_files"], ["README.md"])
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), "new title\nbody\n")

    def test_apply_patch_rejects_escape(self):
        with tempfile.TemporaryDirectory() as workspace:
            tools = WorkspaceTools(Path(workspace))

            with self.assertRaises(ValueError):
                tools.apply_patch(
                    """*** Begin Patch
*** Update File: ../outside.txt
@@
-old
+new
*** End Patch
"""
                )


if __name__ == "__main__":
    unittest.main()
