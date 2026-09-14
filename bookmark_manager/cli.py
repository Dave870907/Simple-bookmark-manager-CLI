"""Command-line interface for the bookmark manager.

Wires argparse subcommands (add, list, search-tag, search-keyword, delete)
to BookmarkRepository, per req-plain-text-output and the CLI-boundary
decisions recorded in the requirements artifact.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from bookmark_manager.repository import (
    Bookmark,
    BookmarkNotFoundError,
    BookmarkRepository,
    DuplicateUrlError,
    InvalidTagsError,
    InvalidUrlError,
    DEFAULT_DB_PATH,
    parse_tags,
)


def format_bookmark(bookmark: Bookmark) -> str:
    tags = ", ".join(bookmark.tags) if bookmark.tags else "(none)"
    return f"[{bookmark.id}] {bookmark.title} — {bookmark.url} (tags: {tags})"


def format_results(bookmarks: Sequence[Bookmark], empty_message: str) -> str:
    if not bookmarks:
        return empty_message
    return "\n".join(format_bookmark(b) for b in bookmarks)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bookmarks",
        description="A simple local bookmark manager backed by SQLite.",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH!r} in the current directory)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a bookmark")
    add_parser.add_argument("url", help="Bookmark URL, e.g. https://example.com")
    add_parser.add_argument("title", help="Bookmark title")
    add_parser.add_argument(
        "--tags",
        default=None,
        help='Optional tags as a JSON array string, e.g. \'["work", "docs"]\'',
    )

    subparsers.add_parser("list", help="List all bookmarks")

    search_tag_parser = subparsers.add_parser(
        "search-tag", help="Find bookmarks with an exact tag match"
    )
    search_tag_parser.add_argument("tag", help="Tag to match exactly")

    search_keyword_parser = subparsers.add_parser(
        "search-keyword", help="Find bookmarks whose title or URL contains a keyword"
    )
    search_keyword_parser.add_argument("keyword", help="Keyword to search for")

    delete_parser = subparsers.add_parser("delete", help="Delete a bookmark by ID")
    delete_parser.add_argument("id", type=int, help="Bookmark ID to delete")

    return parser


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        with BookmarkRepository(args.db) as repo:
            if args.command == "add":
                tags = parse_tags(args.tags)
                bookmark = repo.add(args.url, args.title, tags)
                print(f"Added bookmark {bookmark.id}: {bookmark.title}")
            elif args.command == "list":
                print(format_results(repo.list_all(), "No bookmarks found."))
            elif args.command == "search-tag":
                print(
                    format_results(
                        repo.search_by_tag(args.tag),
                        f"No bookmarks found with tag '{args.tag}'.",
                    )
                )
            elif args.command == "search-keyword":
                print(
                    format_results(
                        repo.search_by_keyword(args.keyword),
                        f"No bookmarks found matching '{args.keyword}'.",
                    )
                )
            elif args.command == "delete":
                repo.delete(args.id)
                print(f"Deleted bookmark {args.id}")
    except (InvalidUrlError, DuplicateUrlError, InvalidTagsError, BookmarkNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
