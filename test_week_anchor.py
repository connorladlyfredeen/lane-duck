"""Regression test for the "No pools found today" bug.

The scraper anchors each week to Monday of the *current* week, derived from
now_toronto(). If "now" is read off the server's UTC clock instead of Toronto's,
then on a Sunday evening in Toronto (when UTC has already rolled into Monday) the
week anchor jumps forward and the entire current week — including that Sunday,
which users still consider "today" — is emitted with next week's dates and thus
dropped from the output.

These tests pin now_toronto() to a Sunday evening in Toronto and assert that
convert_to_new_format() produces the correct current-week date for every
weekday, i.e. Mon 2026-07-06 through Sun 2026-07-12.
"""
import unittest
from datetime import datetime
from unittest.mock import patch

import pytz

import scrape

TORONTO = pytz.timezone("America/Toronto")

# Sunday 2026-07-12, 8:30pm Toronto time. At this instant UTC is already
# Monday 2026-07-13 00:30 — the exact condition that triggered the bug.
SUNDAY_EVENING_ET = TORONTO.localize(datetime(2026, 7, 12, 20, 30))

# The current week (Mon..Sun) that must appear in the output.
EXPECTED = {
    "Monday": "2026-07-06",
    "Tuesday": "2026-07-07",
    "Wednesday": "2026-07-08",
    "Thursday": "2026-07-09",
    "Friday": "2026-07-10",
    "Saturday": "2026-07-11",
    "Sunday": "2026-07-12",
}


def _session(day):
    return {"id": 1, "day": day, "title": "1:00 PM - 2:00 PM", "status": "active"}


class SundayEveningWeekAnchor(unittest.TestCase):
    def test_full_current_week_including_sunday(self):
        with patch.object(scrape, "now_toronto", return_value=SUNDAY_EVENING_ET):
            for day, expected_date in EXPECTED.items():
                out = scrape.convert_to_new_format(_session(day), week_offset=0)
                self.assertEqual(
                    out["start_time"][:10], expected_date,
                    f"{day} should anchor to {expected_date} (current week), got {out['start_time']}",
                )

    def test_sunday_is_today_not_a_week_late(self):
        # The specific regression: Sunday must be today's date, not +7 days.
        with patch.object(scrape, "now_toronto", return_value=SUNDAY_EVENING_ET):
            out = scrape.convert_to_new_format(_session("Sunday"), week_offset=0)
        self.assertEqual(out["start_time"][:10], "2026-07-12")
        self.assertNotEqual(out["start_time"][:10], "2026-07-19")


if __name__ == "__main__":
    unittest.main(verbosity=2)
