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


class StatsCommandTests(CliTestCase):
    """BR-STATS-01 through BR-STATS-05"""

    def test_stats_no_bookmarks(self) -> None:
        exit_code, out, err = self.run_cli("stats")
        self.assertEqual(exit_code, 0)
        self.assertIn("No bookmarks found.", out)
        self.assertEqual(err, "")

    def test_stats_default_view_is_domain(self) -> None:
        self.run_cli("add", "https://github.com/a", "A")
        self.run_cli("add", "https://github.com/b", "B")
        exit_code, out, _ = self.run_cli("stats")
        self.assertEqual(exit_code, 0)
        self.assertIn("github.com", out)
        self.assertIn("100.0%", out)
        self.assertIn("(2)", out)

    def test_stats_by_domain_groups_www_variant(self) -> None:
        self.run_cli("add", "https://github.com/a", "A")
        self.run_cli("add", "https://www.github.com/b", "B")
        exit_code, out, _ = self.run_cli("stats", "--by", "domain")
        self.assertEqual(exit_code, 0)
        self.assertIn("github.com", out)
        self.assertIn("(2)", out)

    def test_stats_by_tag_no_tags_recorded(self) -> None:
        self.run_cli("add", "https://a.com", "A")
        exit_code, out, err = self.run_cli("stats", "--by", "tag")
        self.assertEqual(exit_code, 0)
        self.assertIn("No tags recorded yet.", out)
        self.assertEqual(err, "")

    def test_stats_by_tag_shows_tag_distribution(self) -> None:
        self.run_cli("add", "https://a.com", "A", "--tags", '["python", "docs"]')
        self.run_cli("add", "https://b.com", "B", "--tags", '["python"]')
        exit_code, out, _ = self.run_cli("stats", "--by", "tag")
        self.assertEqual(exit_code, 0)
        self.assertIn("python", out)
        self.assertIn("docs", out)

    def test_stats_invalid_by_value_errors(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                run(["--db", self.db_path, "stats", "--by", "bogus"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("invalid choice", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
