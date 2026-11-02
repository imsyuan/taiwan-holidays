#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/generate_ics.py 的單元測試（僅標準函式庫 unittest；有裝 icalendar 時多一層解析驗證）。

    python3 -m unittest discover -s scripts

事件數的斷言是「釘住」目前 data/ 的內容（2026：22 筆國定假日、0 筆補班；2027：24 筆、0 筆；
全部年度合計 194 筆國定假日、22 筆補班）。政府修正辦公日曆、data/ 更新後，請核對新數字再更新這裡。
"""

import json
import re
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_ics as gi  # noqa: E402

try:
    import icalendar  # type: ignore
except ImportError:  # pragma: no cover
    icalendar = None

DATA = Path(__file__).resolve().parent.parent / "data"


def unfold(text):
    """RFC 5545 還原折行：CRLF 後接一個空白或 Tab 就是續行。"""
    return re.sub(r"\r\n[ \t]", "", text)


def events_of(year, kind=None):
    return [e for e in gi.build_events() if e["date"].year == year and (kind is None or e["kind"] == kind)]


class Escaping(unittest.TestCase):
    def test_escapes_backslash_semicolon_comma_newline(self):
        self.assertEqual(gi.escape_text("a,b;c\\d\ne"), "a\\,b\\;c\\\\d\\ne")

    def test_backslash_is_escaped_first_not_double_escaped(self):
        self.assertEqual(gi.escape_text("\\;"), "\\\\\\;")

    def test_crlf_and_cr_become_single_escaped_newline(self):
        self.assertEqual(gi.escape_text("a\r\nb\rc"), "a\\nb\\nc")

    def test_chinese_text_untouched(self):
        self.assertEqual(gi.escape_text("春節"), "春節")


class Folding(unittest.TestCase):
    def test_short_line_not_folded(self):
        self.assertEqual(gi.fold_line("SUMMARY:春節"), ["SUMMARY:春節"])

    def test_ascii_fold_at_75_octets_with_leading_space(self):
        line = "DESCRIPTION:" + "a" * 200
        parts = gi.fold_line(line)
        self.assertEqual(len(parts[0].encode("utf-8")), 75)
        for cont in parts[1:]:
            self.assertTrue(cont.startswith(" "))
            self.assertLessEqual(len(cont.encode("utf-8")), 75)
        self.assertEqual("".join([parts[0]] + [p[1:] for p in parts[1:]]), line)

    def test_chinese_folded_by_bytes_never_splits_a_character(self):
        line = "DESCRIPTION:" + "連假與請假攻略，農曆除夕春節" * 12
        parts = gi.fold_line(line)
        self.assertGreater(len(parts), 2)
        for p in parts:
            raw = p.encode("utf-8")  # 若切在字元中間，decode 早就丟 UnicodeDecodeError
            self.assertLessEqual(len(raw), 75)
            self.assertEqual(raw.decode("utf-8"), p)
        self.assertEqual("".join([parts[0]] + [p[1:] for p in parts[1:]]), line)

    def test_fold_boundary_when_next_char_is_three_bytes(self):
        # 前綴 73 位元組＋一個 3 位元組字元 = 76 > 75，字元必須整個移到下一行
        line = "X" * 73 + "春節"
        parts = gi.fold_line(line)
        self.assertEqual(parts[0], "X" * 73)
        self.assertEqual(parts[1], " 春節")

    def test_exactly_75_octets_not_folded(self):
        line = "X" * 75
        self.assertEqual(gi.fold_line(line), [line])


class Rendered(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = gi.render()
        cls.events = gi.build_events()

    def test_crlf_only_and_ends_with_crlf(self):
        self.assertTrue(self.text.endswith("\r\n"))
        self.assertNotRegex(self.text, r"(?<!\r)\n")
        self.assertNotIn("\r\r", self.text)

    def test_every_physical_line_at_most_75_octets(self):
        for line in self.text.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75, line)

    def test_begin_end_balanced_and_nested(self):
        stack = []
        for line in unfold(self.text).split("\r\n"):
            if line.startswith("BEGIN:"):
                stack.append(line[6:])
            elif line.startswith("END:"):
                self.assertTrue(stack and stack[-1] == line[4:], line)
                stack.pop()
        self.assertEqual(stack, [])

    def test_calendar_headers(self):
        lines = unfold(self.text).split("\r\n")
        self.assertEqual(lines[0], "BEGIN:VCALENDAR")
        for expected in ("VERSION:2.0", "X-WR-CALNAME:台灣國定假日與補班日", "X-WR-TIMEZONE:Asia/Taipei",
                         "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D"):
            self.assertIn(expected, lines)

    def test_all_day_events_use_value_date_and_next_day_end(self):
        text = unfold(self.text)
        starts = re.findall(r"DTSTART;VALUE=DATE:(\d{8})\r\nDTEND;VALUE=DATE:(\d{8})", text)
        self.assertEqual(len(starts), len(self.events))
        for s, e in starts:
            sd = date(int(s[:4]), int(s[4:6]), int(s[6:]))
            ed = date(int(e[:4]), int(e[4:6]), int(e[6:]))
            self.assertEqual(ed - sd, timedelta(days=1))
        self.assertNotIn("DTSTART:", text)

    def test_url_in_description_and_url_property(self):
        text = unfold(self.text)
        self.assertEqual(text.count("DESCRIPTION:"), len(self.events))
        for ev in self.events:
            self.assertTrue(ev["url"].startswith("https://tw-holidays.gooliya.com/"))
            self.assertIn(ev["url"], ev["description"])

    @unittest.skipIf(icalendar is None, "未安裝 icalendar，略過套件解析驗證")
    def test_parses_with_icalendar_package(self):
        cal = icalendar.Calendar.from_ical(self.text.encode("utf-8"))
        vevents = [c for c in cal.walk() if c.name == "VEVENT"]
        self.assertEqual(len(vevents), len(self.events))
        self.assertEqual(str(cal["X-WR-CALNAME"]), "台灣國定假日與補班日")
        first = vevents[0]
        self.assertEqual(first["DTSTART"].dt, date(2017, 1, 1))
        self.assertEqual(first["DTEND"].dt, date(2017, 1, 2))


class Uids(unittest.TestCase):
    def test_uid_format_and_uniqueness(self):
        events = gi.build_events()
        uids = [e["uid"] for e in events]
        self.assertEqual(len(uids), len(set(uids)))
        for e in events:
            self.assertEqual(e["uid"], f"{e['date'].strftime('%Y%m%d')}-{e['kind']}@tw-holidays.gooliya.com")

    def test_known_uids_are_stable(self):
        uids = {e["uid"] for e in gi.build_events()}
        self.assertIn("20260101-holiday@tw-holidays.gooliya.com", uids)  # 開國紀念日
        self.assertIn("20250208-makeup@tw-holidays.gooliya.com", uids)  # 補行上班

    def test_uid_unchanged_when_other_days_change(self):
        """UID 只由日期與類型決定，與事件在檔案中的順序、其他事件無關。"""
        full = {e["uid"] for e in gi.build_events()}
        only_2026 = {e["uid"] for e in gi.build_events(years=[2026])}
        self.assertTrue(only_2026 < full)


class Idempotent(unittest.TestCase):
    def test_render_twice_identical(self):
        self.assertEqual(gi.render(), gi.render())

    def test_committed_file_matches_generator(self):
        """calendar/tw-holidays.ics 必須是最新產物（等同 generate_ics.py --check）。"""
        self.assertEqual(gi.OUT_PATH.read_bytes(), gi.render().encode("utf-8"))


class EventCounts(unittest.TestCase):
    def test_2026_counts(self):
        self.assertEqual(len(events_of(2026, "holiday")), 22)
        self.assertEqual(len(events_of(2026, "makeup")), 0)

    def test_2027_counts(self):
        self.assertEqual(len(events_of(2027, "holiday")), 24)
        self.assertEqual(len(events_of(2027, "makeup")), 0)

    def test_totals_across_all_years(self):
        events = gi.build_events()
        self.assertEqual(sum(1 for e in events if e["kind"] == "holiday"), 194)
        self.assertEqual(sum(1 for e in events if e["kind"] == "makeup"), 22)
        self.assertEqual(len(events), 216)

    def test_counts_match_published_json_for_every_year(self):
        for year in gi.load_years():
            holidays = json.loads((DATA / str(year) / "holidays.json").read_text(encoding="utf-8"))
            makeup = json.loads((DATA / str(year) / "makeup-workdays.json").read_text(encoding="utf-8"))
            self.assertEqual(len(events_of(year, "holiday")), len(holidays), f"{year} 國定假日")
            self.assertEqual(len(events_of(year, "makeup")), len(makeup), f"{year} 補班日")
            self.assertEqual({e["date"].strftime("%Y%m%d") for e in events_of(year, "holiday")},
                             {h["date"] for h in holidays})
            self.assertEqual({e["date"].strftime("%Y%m%d") for e in events_of(year, "makeup")},
                             {m["date"] for m in makeup})

    def test_plain_weekends_are_not_events(self):
        # 2026-01-03 是週六、沒有名稱
        self.assertNotIn(date(2026, 1, 3), {e["date"] for e in events_of(2026)})


class MakeupTitles(unittest.TestCase):
    def test_makeup_title_prefix(self):
        makeups = [e for e in gi.build_events() if e["kind"] == "makeup"]
        self.assertEqual(len(makeups), 22)
        for e in makeups:
            self.assertTrue(e["summary"].startswith("補班："), e["summary"])
            self.assertIn("這天要上班", e["description"])

    def test_known_makeup_day(self):
        ev = next(e for e in gi.build_events() if e["uid"].startswith("20250208-makeup"))
        self.assertEqual(ev["summary"], "補班：補行上班")

    def test_holiday_title_is_plain_description(self):
        ev = next(e for e in gi.build_events() if e["uid"].startswith("20260101-holiday"))
        self.assertEqual(ev["summary"], "開國紀念日")


class Urls(unittest.TestCase):
    def test_run_day_links_to_run_page_that_exists(self):
        ev = next(e for e in gi.build_events() if e["uid"].startswith("20260216-holiday"))  # 農曆除夕
        self.assertEqual(ev["url"], "https://tw-holidays.gooliya.com/2026/lunar-new-year/")
        self.assertTrue((gi.ROOT / "2026" / "lunar-new-year" / "index.html").is_file())

    def test_year_without_pages_falls_back_to_home(self):
        ev = next(e for e in gi.build_events() if e["uid"].startswith("20200101-holiday"))
        self.assertEqual(ev["url"], "https://tw-holidays.gooliya.com/")
        self.assertIn("台灣國定假日行事曆", ev["description"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
