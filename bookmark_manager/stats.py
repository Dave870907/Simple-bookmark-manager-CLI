"""Pure aggregation and rendering logic for the `stats` CLI subcommand.

Computes domain/tag frequency distributions from bookmarks and renders them
as a plain-ASCII bar chart, per BR-STATS-01 through BR-STATS-15 in the
business-rules artifact. Kept free of I/O, argparse, and print so the
counting/bucketing/rendering logic is unit-testable without a database or
captured stdout — mirrors how validate_url/parse_tags in repository.py are
already tested as pure functions.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from bookmark_manager.repository import Bookmark

MAX_BUCKETS = 10
MAX_BAR_WIDTH = 30
OTHER_LABEL = "Other"

StatsView = Literal["domain", "tag"]


@dataclass(frozen=True)
class StatsBucket:
    """A single row in a stats report (BR-STATS-10, BR-STATS-11)."""

    label: str
    count: int
    percentage: float


@dataclass(frozen=True)
class StatsReport:
    """A computed, transient frequency-distribution report.

    Never persisted — recomputed fresh from `BookmarkRepository.list_all()`
    on every `stats` invocation.
    """

    view: StatsView
    total: int
    buckets: list[StatsBucket]


def extract_domain(url: str) -> str:
    """Return the normalized domain bucket key for `url` (BR-STATS-06).

    Strips userinfo and port, lowercases the host, and drops a leading
    "www." prefix, so URLs that differ only by scheme, case, `www.`,
    userinfo, or port land in the same domain bucket. Every stored bookmark
    URL already passed `validate_url` at add-time (req-url-validation), so
    this always finds a non-empty netloc for stored data (BR-STATS-07).
    """
    netloc = urlparse(url).netloc
    host = netloc.split("@")[-1]
    host = host.split(":")[0]
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def compute_domain_stats(bookmarks: list[Bookmark]) -> StatsReport:
    """Frequency distribution over bookmark domains.

    Denominator is the bookmark count: each bookmark contributes exactly one
    domain (BR-STATS-08).
    """
    counts = Counter(extract_domain(b.url) for b in bookmarks)
    return _build_report("domain", counts, total=len(bookmarks))


def compute_tag_stats(bookmarks: list[Bookmark]) -> StatsReport:
    """Frequency distribution over tag assignments.

    Denominator is the total tag-assignment count, not the bookmark count: a
    bookmark with several tags contributes to several buckets (BR-STATS-09).
    """
    counts = Counter(tag for b in bookmarks for tag in b.tags)
    return _build_report("tag", counts, total=sum(counts.values()))


def _build_report(view: StatsView, counts: Counter[str], total: int) -> StatsReport:
    """Rank, cap at the top 10 (+"Other"), and attach percentages.

    Sort is count descending, then label ascending case-insensitive, for
    deterministic output (BR-STATS-10). Entries beyond the top 10 are
    collapsed into a trailing "Other" bucket, appended last regardless of
    its own count (BR-STATS-11).
    """
    if total == 0:
        return StatsReport(view=view, total=0, buckets=[])

    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    top, rest = ranked[:MAX_BUCKETS], ranked[MAX_BUCKETS:]

    buckets = [
        StatsBucket(label=label, count=count, percentage=count / total * 100)
        for label, count in top
    ]
    if rest:
        other_count = sum(count for _, count in rest)
        buckets.append(
            StatsBucket(
                label=OTHER_LABEL,
                count=other_count,
                percentage=other_count / total * 100,
            )
        )

    return StatsReport(view=view, total=total, buckets=buckets)


def render_bar(percentage: float) -> str:
    """Render a plain-ASCII bar proportional to `percentage` of the total.

    Width is `round(percentage / 100 * MAX_BAR_WIDTH)` (BR-STATS-13). Any
    nonzero percentage renders at least one `#` so small shares stay visible
    (BR-STATS-14).
    """
    width = round(percentage / 100 * MAX_BAR_WIDTH)
    if percentage > 0 and width == 0:
        width = 1
    return "#" * width
