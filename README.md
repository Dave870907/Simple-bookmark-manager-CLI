# Simple Bookmark Manager CLI

A lightweight, local, single-user command-line tool for saving bookmarks
(URL + title + optional tags) and finding them again by tag or keyword.
Bookmarks are stored in a local SQLite database — no server, no network
dependency, no account.

## Requirements

- Python 3.9+ (standard library only — no external dependencies)

## Important: database location

The SQLite database file (`bookmarks.db` by default) is created **relative
to the current working directory** the first time you run a command. This
is intentional for this proof of concept: running the tool from different
directories gives you independent, unlinked bookmark stores. Run the CLI
from the same directory every time if you want a single, consistent set of
bookmarks, or pass `--db /path/to/bookmarks.db` to pin an explicit location.

## Usage

Run the CLI as a module from the project root:

```bash
python3 -m bookmark_manager <command> [arguments]
```

### Add a bookmark

```bash
python3 -m bookmark_manager add https://example.com "Example Site"
python3 -m bookmark_manager add https://docs.python.org "Python Docs" --tags '["python", "reference"]'
```

- The URL must be well-formed with an `http://` or `https://` scheme.
- The URL must not already exist in the store (duplicates are rejected).
- `--tags` is optional and must be a JSON array of strings when provided.

### List all bookmarks

```bash
python3 -m bookmark_manager list
```

Example output:

```
[1] Example Site — https://example.com (tags: (none))
[2] Python Docs — https://docs.python.org (tags: python, reference)
```

### Search by exact tag

```bash
python3 -m bookmark_manager search-tag python
```

Returns every bookmark whose tag list contains an exact match for the
given tag.

### Search by keyword

```bash
python3 -m bookmark_manager search-keyword docs
```

Returns every bookmark whose title or URL contains the given keyword
(case-insensitive substring match). Tags are not searched by this command
— use `search-tag` for tag lookups.

### Delete a bookmark

```bash
python3 -m bookmark_manager delete 1
```

Deletes the bookmark with the given ID. If no bookmark with that ID
exists, the command prints a clear error to stderr and exits with a
non-zero status.

### View stats

```bash
python3 -m bookmark_manager stats
python3 -m bookmark_manager stats --by tag
```

Prints a plain-ASCII horizontal bar chart of your most-bookmarked domains
(the default) or your most-used tags. Domain percentages are share of total
bookmarks; tag percentages are share of total tag assignments (a bookmark
with several tags counts toward each of its tags). At most the top 10
entries are shown by name; anything beyond that is folded into a trailing
`Other` bucket. Example output:

```
github.com   ######################          75.0% (3)
example.com  ########                        25.0% (1)
```

If there are no bookmarks, prints `No bookmarks found.` If `--by tag` is
used but no bookmark has any tags, prints `No tags recorded yet.` Both are
normal, non-error outcomes (exit code 0).

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

Tests cover the success and failure paths for every operation: add
(success, duplicate URL, malformed URL, malformed tags), list (empty and
non-empty), search-tag (match and no match), search-keyword (match and no
match), delete (success and missing ID), and stats (domain/tag aggregation,
bucketing, bar rendering, and both empty states).

## Out of scope for this proof of concept

Editing existing bookmarks, import/export, cross-device sync, multi-user
support/authentication, and packaging/distribution are intentionally not
implemented.
