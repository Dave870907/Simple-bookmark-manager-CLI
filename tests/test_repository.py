"""Unit tests for BookmarkRepository CRUD operations.

Each test class maps to one requirement from the requirements artifact
(req-add-bookmark, req-url-validation, req-url-uniqueness,
req-list-bookmarks, req-search-by-tag, req-search-by-keyword,
req-delete-bookmark, req-delete-error-handling, req-sqlite-persistence).
"""

from __future__ import annotations

import os
import tempfile
import unittest

from bookmark_manager.repository import (
    BookmarkNotFoundError,
    BookmarkRepository,
    DuplicateUrlError,
    InvalidTagsError,
    InvalidUrlError,
    parse_tags,
)


class RepositoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "bookmarks.db")
        self.repo = BookmarkRepository(self.db_path)

    def tearDown(self) -> None:
        self.repo.close()
        self._tmpdir.cleanup()


class AddBookmarkTests(RepositoryTestCase):
    """req-add-bookmark"""

    def test_add_with_tags_persists_bookmark(self) -> None:
        bookmark = self.repo.add(
            "https://example.com", "Example", ["work", "docs"]
        )
        self.assertEqual(bookmark.tags, ["work", "docs"])
        self.assertEqual(self.repo.list_all(), [bookmark])

    def test_add_without_tags_defaults_to_empty_list(self) -> None:
        bookmark = self.repo.add("https://example.com", "Example")
        self.assertEqual(bookmark.tags, [])


class ParseTagsTests(unittest.TestCase):
    """req-add-bookmark: tags-as-JSON-array CLI boundary"""

    def test_valid_json_array_parses(self) -> None:
        self.assertEqual(parse_tags('["a", "b"]'), ["a", "b"])

    def test_none_defaults_to_empty_list(self) -> None:
        self.assertEqual(parse_tags(None), [])

    def test_invalid_json_raises(self) -> None:
        with self.assertRaises(InvalidTagsError):
            parse_tags("not-json")

    def test_non_array_json_raises(self) -> None:
        with self.assertRaises(InvalidTagsError):
            parse_tags('{"a": 1}')


class UrlValidationTests(RepositoryTestCase):
    """req-url-validation"""

    def test_missing_scheme_is_rejected(self) -> None:
        with self.assertRaises(InvalidUrlError):
            self.repo.add("example.com", "Example")
        self.assertEqual(self.repo.list_all(), [])

    def test_well_formed_https_url_is_accepted(self) -> None:
        bookmark = self.repo.add("https://example.com", "Example")
        self.assertEqual(bookmark.url, "https://example.com")


class UrlUniquenessTests(RepositoryTestCase):
    """req-url-uniqueness"""

    def test_duplicate_url_is_rejected(self) -> None:
        self.repo.add("https://example.com", "Example")
        with self.assertRaises(DuplicateUrlError):
            self.repo.add("https://example.com", "Example Again")
        self.assertEqual(len(self.repo.list_all()), 1)


class ListBookmarksTests(RepositoryTestCase):
    """req-list-bookmarks"""

    def test_empty_store_returns_empty_list(self) -> None:
        self.assertEqual(self.repo.list_all(), [])

    def test_lists_all_bookmarks_in_id_order(self) -> None:
        first = self.repo.add("https://a.com", "A")
        second = self.repo.add("https://b.com", "B")
        self.assertEqual(self.repo.list_all(), [first, second])


class SearchByTagTests(RepositoryTestCase):
    """req-search-by-tag"""

    def test_returns_bookmarks_with_exact_tag_match(self) -> None:
        tagged = self.repo.add("https://a.com", "A", ["work"])
        self.repo.add("https://b.com", "B", ["personal"])
        self.assertEqual(self.repo.search_by_tag("work"), [tagged])

    def test_no_match_returns_empty_list(self) -> None:
        self.repo.add("https://a.com", "A", ["personal"])
        self.assertEqual(self.repo.search_by_tag("work"), [])


class SearchByKeywordTests(RepositoryTestCase):
    """req-search-by-keyword"""

    def test_matches_title_case_insensitively(self) -> None:
        bookmark = self.repo.add("https://a.com", "Great Recipes")
        self.assertEqual(self.repo.search_by_keyword("recipes"), [bookmark])

    def test_matches_url(self) -> None:
        bookmark = self.repo.add("https://cooking.example.com", "Site")
        self.assertEqual(self.repo.search_by_keyword("cooking"), [bookmark])

    def test_no_match_returns_empty_list(self) -> None:
        self.repo.add("https://a.com", "A")
        self.assertEqual(self.repo.search_by_keyword("zzz"), [])


class DeleteBookmarkTests(RepositoryTestCase):
    """req-delete-bookmark"""

    def test_delete_removes_bookmark(self) -> None:
        bookmark = self.repo.add("https://a.com", "A")
        self.repo.delete(bookmark.id)
        self.assertEqual(self.repo.list_all(), [])


class DeleteErrorHandlingTests(RepositoryTestCase):
    """req-delete-error-handling"""

    def test_deleting_missing_id_raises(self) -> None:
        with self.assertRaises(BookmarkNotFoundError):
            self.repo.delete(999)


class SqlitePersistenceTests(RepositoryTestCase):
    """req-sqlite-persistence"""

    def test_data_persists_across_repository_instances(self) -> None:
        bookmark = self.repo.add("https://a.com", "A")
        self.repo.close()

        reopened = BookmarkRepository(self.db_path)
        try:
            self.assertEqual(reopened.list_all(), [bookmark])
        finally:
            reopened.close()


if __name__ == "__main__":
    unittest.main()
