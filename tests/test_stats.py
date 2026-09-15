"""Unit tests for the pure stats aggregation/rendering logic.

Each test class maps to a business rule from the stats-business-rules
artifact (BR-STATS-06 through BR-STATS-14).
"""

from __future__ import annotations

import unittest

from bookmark_manager.repository import Bookmark
from bookmark_manager.stats import (
    MAX_BAR_WIDTH,
    compute_domain_stats,
    compute_tag_stats,
    extract_domain,
    render_bar,
)


def _bookmark(id_: int, url: str, tags: list[str] | None = None) -> Bookmark:
    return Bookmark(id=id_, url=url, title=f"Title {id_}", tags=tags or [])


class ExtractDomainTests(unittest.TestCase):
    """BR-STATS-06, BR-STATS-07"""

    def test_plain_host(self) -> None:
        self.assertEqual(extract_domain("https://example.com"), "example.com")

    def test_strips_www_prefix(self) -> None:
        self.assertEqual(extract_domain("https://www.github.com"), "github.com")

    def test_lowercases_host(self) -> None:
        self.assertEqual(extract_domain("https://WWW.GitHub.com"), "github.com")

    def test_strips_port(self) -> None:
        self.assertEqual(extract_domain("https://example.com:8443/path"), "example.com")

    def test_strips_userinfo(self) -> None:
        self.assertEqual(
            extract_domain("https://user:pass@example.com"), "example.com"
        )

    def test_combined_normalization(self) -> None:
        self.assertEqual(
            extract_domain("https://user:pass@WWW.GitHub.com:8443/repo"),
            "github.com",
        )


class ComputeDomainStatsTests(unittest.TestCase):
    """BR-STATS-08"""

    def test_denominator_is_bookmark_count(self) -> None:
        bookmarks = [
            _bookmark(1, "https://github.com/a"),
            _bookmark(2, "https://github.com/b"),
            _bookmark(3, "https://example.com"),
        ]
        report = compute_domain_stats(bookmarks)
        self.assertEqual(report.total, 3)
        github = next(b for b in report.buckets if b.label == "github.com")
        self.assertEqual(github.count, 2)
        self.assertAlmostEqual(github.percentage, 200 / 3)

    def test_www_variants_grouped_together(self) -> None:
        bookmarks = [
            _bookmark(1, "https://github.com/a"),
            _bookmark(2, "https://www.github.com/b"),
        ]
        report = compute_domain_stats(bookmarks)
        self.assertEqual(len(report.buckets), 1)
        self.assertEqual(report.buckets[0].count, 2)

    def test_empty_bookmarks_yields_empty_report(self) -> None:
        report = compute_domain_stats([])
        self.assertEqual(report.total, 0)
        self.assertEqual(report.buckets, [])


class ComputeTagStatsTests(unittest.TestCase):
    """BR-STATS-09"""

    def test_denominator_is_tag_assignment_count(self) -> None:
        bookmarks = [
            _bookmark(1, "https://a.com", ["work", "docs"]),
            _bookmark(2, "https://b.com", ["work"]),
        ]
        report = compute_tag_stats(bookmarks)
        self.assertEqual(report.total, 3)
        work = next(b for b in report.buckets if b.label == "work")
        self.assertEqual(work.count, 2)
        self.assertAlmostEqual(work.percentage, 200 / 3)

    def test_no_tags_recorded_yields_zero_total(self) -> None:
        bookmarks = [_bookmark(1, "https://a.com"), _bookmark(2, "https://b.com")]
        report = compute_tag_stats(bookmarks)
        self.assertEqual(report.total, 0)
        self.assertEqual(report.buckets, [])

    def test_bookmark_with_many_tags_counts_each_tag(self) -> None:
        bookmarks = [_bookmark(1, "https://a.com", ["x", "y", "z"])]
        report = compute_tag_stats(bookmarks)
        self.assertEqual(report.total, 3)
        self.assertEqual({b.label for b in report.buckets}, {"x", "y", "z"})


class RankingAndBucketingTests(unittest.TestCase):
    """BR-STATS-10, BR-STATS-11"""

    def test_sorted_by_count_descending(self) -> None:
        bookmarks = [
            _bookmark(1, "https://rare.com"),
            _bookmark(2, "https://common.com/1"),
            _bookmark(3, "https://common.com/2"),
        ]
        report = compute_domain_stats(bookmarks)
        self.assertEqual([b.label for b in report.buckets], ["common.com", "rare.com"])

    def test_ties_broken_by_label_ascending_case_insensitive(self) -> None:
        bookmarks = [
            _bookmark(1, "https://Zebra.com"),
            _bookmark(2, "https://alpha.com"),
        ]
        report = compute_domain_stats(bookmarks)
        self.assertEqual([b.label for b in report.buckets], ["alpha.com", "zebra.com"])

    def test_more_than_ten_distinct_values_collapse_into_other(self) -> None:
        bookmarks = [_bookmark(i, f"https://domain{i}.com") for i in range(12)]
        report = compute_domain_stats(bookmarks)
        self.assertEqual(len(report.buckets), 11)
        self.assertEqual(report.buckets[-1].label, "Other")
        self.assertEqual(report.buckets[-1].count, 2)

    def test_ten_or_fewer_distinct_values_have_no_other_bucket(self) -> None:
        bookmarks = [_bookmark(i, f"https://domain{i}.com") for i in range(10)]
        report = compute_domain_stats(bookmarks)
        self.assertEqual(len(report.buckets), 10)
        self.assertNotIn("Other", [b.label for b in report.buckets])

    def test_buckets_partition_the_full_total(self) -> None:
        bookmarks = [_bookmark(i, f"https://domain{i}.com") for i in range(15)]
        report = compute_domain_stats(bookmarks)
        self.assertEqual(sum(b.count for b in report.buckets), report.total)


class RenderBarTests(unittest.TestCase):
    """BR-STATS-13, BR-STATS-14"""

    def test_full_percentage_uses_max_width(self) -> None:
        self.assertEqual(render_bar(100.0), "#" * MAX_BAR_WIDTH)

    def test_zero_percentage_renders_no_bar(self) -> None:
        self.assertEqual(render_bar(0.0), "")

    def test_small_nonzero_percentage_renders_minimum_visible_bar(self) -> None:
        self.assertEqual(render_bar(1.0), "#")

    def test_proportional_width(self) -> None:
        self.assertEqual(render_bar(50.0), "#" * 15)


if __name__ == "__main__":
    unittest.main()
