"""Unit tests for the CLI layer (argument wiring, output, exit codes).

Covers req-plain-text-output and the error-handling behavior demanded by
req-url-validation, req-url-uniqueness, and req-delete-error-handling at
the CLI boundary.
"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest

from bookmark_manager.cli import run


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "bookmarks.db")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = run(["--db", self.db_path, *args])
        return exit_code, stdout.getvalue(), stderr.getvalue()


class AddCommandTests(CliTestCase):
    def test_add_success_prints_confirmation(self) -> None:
        exit_code, out, _ = self.run_cli("add", "https://example.com", "Example")
        self.assertEqual(exit_code, 0)
        self.assertIn("Added bookmark", out)

    def test_add_duplicate_url_errors(self) -> None:
        self.run_cli("add", "https://example.com", "Example")
        exit_code, _, err = self.run_cli("add", "https://example.com", "Example 2")
        self.assertEqual(exit_code, 1)
        self.assertIn("already exists", err)

    def test_add_malformed_url_errors(self) -> None:
        exit_code, _, err = self.run_cli("add", "not-a-url", "Example")
        self.assertEqual(exit_code, 1)
        self.assertIn("Invalid URL", err)

    def test_add_malformed_tags_errors(self) -> None:
        exit_code, _, err = self.run_cli(
            "add", "https://example.com", "Example", "--tags", "not-json"
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("Tags must be", err)


class ListCommandTests(CliTestCase):
    def test_list_empty_store(self) -> None:
        exit_code, out, _ = self.run_cli("list")
        self.assertEqual(exit_code, 0)
        self.assertIn("No bookmarks found.", out)

    def test_list_shows_all_bookmarks(self) -> None:
        self.run_cli("add", "https://a.com", "A", "--tags", '["x"]')
        exit_code, out, _ = self.run_cli("list")
        self.assertEqual(exit_code, 0)
        self.assertIn("https://a.com", out)
        self.assertIn("A", out)
        self.assertIn("x", out)


class SearchTagCommandTests(CliTestCase):
    def test_search_tag_match(self) -> None:
        self.run_cli("add", "https://a.com", "A", "--tags", '["work"]')
        exit_code, out, _ = self.run_cli("search-tag", "work")
        self.assertEqual(exit_code, 0)
        self.assertIn("https://a.com", out)

    def test_search_tag_no_match(self) -> None:
        exit_code, out, _ = self.run_cli("search-tag", "missing")
        self.assertEqual(exit_code, 0)
        self.assertIn("No bookmarks found with tag", out)


class SearchKeywordCommandTests(CliTestCase):
    def test_search_keyword_match(self) -> None:
        self.run_cli("add", "https://a.com", "Great Recipes")
        exit_code, out, _ = self.run_cli("search-keyword", "recipes")
        self.assertEqual(exit_code, 0)
        self.assertIn("Great Recipes", out)

    def test_search_keyword_no_match(self) -> None:
        exit_code, out, _ = self.run_cli("search-keyword", "zzz")
        self.assertEqual(exit_code, 0)
        self.assertIn("No bookmarks found matching", out)


class DeleteCommandTests(CliTestCase):
    def test_delete_success(self) -> None:
        self.run_cli("add", "https://a.com", "A")
        exit_code, out, _ = self.run_cli("delete", "1")
        self.assertEqual(exit_code, 0)
        self.assertIn("Deleted bookmark 1", out)

    def test_delete_missing_id_errors(self) -> None:
        exit_code, _, err = self.run_cli("delete", "999")
        self.assertEqual(exit_code, 1)
        self.assertIn("No bookmark found", err)


if __name__ == "__main__":
    unittest.main()
