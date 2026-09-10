"""SQLite-backed storage and business logic for bookmarks.

Implements req-add-bookmark, req-url-validation, req-url-uniqueness,
req-list-bookmarks, req-search-by-tag, req-search-by-keyword,
req-delete-bookmark, req-delete-error-handling, and req-sqlite-persistence
from the requirements artifact.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from urllib.parse import urlparse

DEFAULT_DB_PATH = "bookmarks.db"

_RECOGNIZED_SCHEMES = ("http", "https")


class BookmarkError(Exception):
    """Base class for all bookmark-manager domain errors."""


class InvalidUrlError(BookmarkError):
    """Raised when a URL is missing a recognized scheme (req-url-validation)."""


class DuplicateUrlError(BookmarkError):
    """Raised when a URL already exists in the store (req-url-uniqueness)."""


class InvalidTagsError(BookmarkError):
    """Raised when the supplied tags value is not a JSON array of strings."""


class BookmarkNotFoundError(BookmarkError):
    """Raised when an operation references a bookmark ID that does not exist
    (req-delete-error-handling)."""


@dataclass(frozen=True)
class Bookmark:
    id: int
    url: str
    title: str
    tags: list[str]


def validate_url(url: str) -> None:
    """Raise InvalidUrlError unless the URL has a recognized scheme."""
    parsed = urlparse(url)
    if parsed.scheme not in _RECOGNIZED_SCHEMES or not parsed.netloc:
        raise InvalidUrlError(
            f"Invalid URL '{url}': must be a well-formed http:// or https:// URL"
        )


def parse_tags(tags_json: str | None) -> list[str]:
    """Parse a JSON array string of tags, defaulting to an empty list.

    Raises InvalidTagsError if the value is not valid JSON or not a list of
    strings.
    """
    if tags_json is None or tags_json == "":
        return []
    try:
        tags = json.loads(tags_json)
    except json.JSONDecodeError as exc:
        raise InvalidTagsError(f"Tags must be a valid JSON array: {exc}") from exc
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise InvalidTagsError("Tags must be a JSON array of strings")
    return tags


class BookmarkRepository:
    """CRUD access to the bookmarks SQLite store."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "BookmarkRepository":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def add(self, url: str, title: str, tags: list[str] | None = None) -> Bookmark:
        """Add a bookmark. Raises InvalidUrlError or DuplicateUrlError."""
        validate_url(url)
        tags = tags or []
        existing = self._conn.execute(
            "SELECT id FROM bookmarks WHERE url = ?", (url,)
        ).fetchone()
        if existing is not None:
            raise DuplicateUrlError(f"Bookmark with URL '{url}' already exists")

        cursor = self._conn.execute(
            "INSERT INTO bookmarks (url, title, tags) VALUES (?, ?, ?)",
            (url, title, json.dumps(tags)),
        )
        self._conn.commit()
        return Bookmark(id=cursor.lastrowid, url=url, title=title, tags=tags)

    def list_all(self) -> list[Bookmark]:
        """Return all bookmarks ordered by ID (req-list-bookmarks)."""
        rows = self._conn.execute(
            "SELECT id, url, title, tags FROM bookmarks ORDER BY id"
        ).fetchall()
        return [self._row_to_bookmark(row) for row in rows]

    def search_by_tag(self, tag: str) -> list[Bookmark]:
        """Return bookmarks whose tag list contains an exact match for `tag`
        (req-search-by-tag)."""
        return [b for b in self.list_all() if tag in b.tags]

    def search_by_keyword(self, keyword: str) -> list[Bookmark]:
        """Return bookmarks whose title or URL contains `keyword`, case
        insensitive (req-search-by-keyword)."""
        needle = keyword.lower()
        return [
            b
            for b in self.list_all()
            if needle in b.title.lower() or needle in b.url.lower()
        ]

    def delete(self, bookmark_id: int) -> None:
        """Delete a bookmark by ID. Raises BookmarkNotFoundError if missing
        (req-delete-bookmark, req-delete-error-handling)."""
        cursor = self._conn.execute(
            "DELETE FROM bookmarks WHERE id = ?", (bookmark_id,)
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            raise BookmarkNotFoundError(f"No bookmark found with ID {bookmark_id}")

    @staticmethod
    def _row_to_bookmark(row: sqlite3.Row) -> Bookmark:
        return Bookmark(
            id=row["id"],
            url=row["url"],
            title=row["title"],
            tags=json.loads(row["tags"]),
        )
