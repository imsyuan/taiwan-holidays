#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/generate_pages.py 的單元測試（僅標準函式庫 unittest）。

    python3 scripts/test_generate_pages.py
    python3 -m unittest scripts.test_generate_pages -v

Parity 測試比對 Python 移植版的 optimize_leave 與 TypeScript 引擎（mcp/src/engine/index.ts）
輸出的 golden 檔 scripts/golden/leave_plans.json。golden 檔的重新產生方式：

    cd mcp && npx --yes tsx@4 scripts/dump-leave-plans.ts && cd ..

其餘測試：slug 年內唯一、連假命名優先序、過去年度不產生頁面、JSON-LD 可解析、
title／description 不重複、站內連結都指向存在的檔案。
"""

import json
import re
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_pages as gp  # noqa: E402

GOLDEN = Path(__file__).resolve().parent / "golden" / "leave_plans.json"


def synthetic_calendar(start, days, holidays=None, workday_weekend=()):
    """產生測試用行事曆：週末放假、指定日期放假並標名稱。"""
    holidays = holidays or {}
    cal = []
    for i in range(days):
        d = start + timedelta(days=i)
        compact = d.strftime("%Y%m%d")
        desc = holidays.get(compact, "")
        off = compact in holidays or (d.weekday() >= 5 and compact not in workday_weekend)
        if compact in workday_weekend:
            desc = "補行上班"
        cal.append({"date": compact, "week": gp.WEEK_CHARS[d.weekday()], "isHoliday": off, "description": desc})
    return cal


class LeaveEngineParity(unittest.TestCase):
    """Python 版 optimize_leave 必須與 TS 引擎的 golden 輸出完全一致。"""

    @classmethod
    def setUpClass(cls):
        with open(GOLDEN, encoding="utf-8") as f:
            cls.golden = json.load(f)

    def test_golden_file_covers_2026_and_2027(self):
        self.assertIn("2026", self.golden)
        self.assertIn("2027", self.golden)

    def test_python_plans_equal_typescript_golden(self):
        for year, by_budget in self.golden.items():
            calendar, _, _ = gp.load_year(int(year))
            for budget, expected in by_budget.items():
                with self.subTest(year=year, budget=budget):
                    actual = gp.optimize_leave(calendar, int(budget))
                    # 經 JSON 往返，消除 4 vs 4.0 之類的型別差異；順序也必須相同
                    self.assertEqual(json.loads(json.dumps(actual)), expected)

    def test_plan_order_matches_engine_sort(self):
        plans = gp.optimize_leave(gp.load_year(2027)[0], 5)
        keys = [(-p["efficiency"], -p["totalDaysOff"], p["offRange"]["start"]) for p in plans]
        self.assertEqual(keys, sorted(keys))

    def test_makeup_saturday_counts_as_workday_gap(self):
        # 週六補班 → 上班日，會把兩段假期分開
        cal = synthetic_calendar(date(2030, 1, 1), 14, holidays={"20300101": "開國紀念日"},
                                 workday_weekend=("20300105",))
        days = sorted(cal, key=lambda d: d["date"])
        self.assertTrue(gp.is_makeup_workday(days[4]))
        runs = gp.off_runs(days)
        self.assertIn((0, 0), runs)


class RunNaming(unittest.TestCase):
    def _run(self, descriptions):
        start = date(2030, 1, 5)  # 週六
        entries = [{"date": (start + timedelta(days=i)).strftime("%Y%m%d"), "week": "六",
                    "isHoliday": True, "description": d} for i, d in enumerate(descriptions)]
        return gp.classify_run(entries)

    def test_priority_lunar_new_year_beats_new_year(self):
        slug, label, _ = self._run(["開國紀念日", "春節", "補假"])
        self.assertEqual((slug, label), ("lunar-new-year", "春節"))

    def test_priority_tomb_sweeping_over_children_day_and_buja(self):
        slug, label, _ = self._run(["補假", "兒童節", "清明節"])
        self.assertEqual((slug, label), ("tomb-sweeping", "清明"))

    def test_priority_order_dragon_boat_mid_autumn_national_day(self):
        self.assertEqual(self._run(["中秋節", "端午節"])[0], "dragon-boat")
        self.assertEqual(self._run(["國慶日", "中秋節"])[0], "mid-autumn")
        self.assertEqual(self._run(["開國紀念日", "國慶日"])[0], "national-day")

    def test_never_named_after_buja_or_adjustment(self):
        slug, label, _ = self._run(["補假", "", "彈性放假"])
        self.assertTrue(slug.startswith("holiday-"))
        self.assertNotIn("補假", label)
        self.assertNotIn("調整", label)
        self.assertNotIn("彈性", label)
        self.assertEqual(slug, "holiday-0105")

    def test_real_2027_runs_use_expected_slugs_and_names(self):
        runs = gp.find_runs(gp.load_year(2027)[0])
        self.assertEqual(
            [r["slug"] for r in runs],
            ["new-year", "lunar-new-year", "peace-memorial-day", "tomb-sweeping", "labor-day",
             "national-day", "taiwan-retrocession-day", "constitution-day"],
        )
        for r in runs:
            self.assertFalse(r["name"].startswith("補假"), r["name"])
            self.assertGreaterEqual(r["length"], gp.MIN_RUN_DAYS)

    def test_real_2026_mid_autumn_run_includes_teachers_day_but_named_mid_autumn(self):
        runs = {r["slug"]: r for r in gp.find_runs(gp.load_year(2026)[0])}
        self.assertIn("mid-autumn", runs)
        self.assertIn("孔子誕辰紀念日/教師節", runs["mid-autumn"]["holiday_names"])


class SlugUniqueness(unittest.TestCase):
    def test_unique_slugs_helper_suffixes_duplicates(self):
        self.assertEqual(gp.unique_slugs(["a", "b", "a", "a"]), ["a", "b", "a-2", "a-3"])

    def test_two_runs_with_same_group_get_distinct_slugs(self):
        # 兩段互不相連、都含「春節」的假期（合成資料）
        cal = synthetic_calendar(date(2030, 1, 7), 21, holidays={
            "20300108": "春節", "20300109": "春節", "20300110": "春節",
            "20300122": "春節", "20300123": "春節", "20300124": "春節",
        })
        runs = gp.find_runs(cal)
        slugs = [r["slug"] for r in runs]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(slugs, ["lunar-new-year", "lunar-new-year-2"])

    def test_real_years_have_unique_slugs(self):
        for y in gp.load_years():
            runs = gp.find_runs(gp.load_year(y)[0])
            slugs = [r["slug"] for r in runs]
            self.assertEqual(len(slugs), len(set(slugs)), f"{y}: {slugs}")


class YearSelection(unittest.TestCase):
    def test_select_years_drops_past_years(self):
        years = [2024, 2025, 2026, 2027]
        self.assertEqual(gp.select_years(years, date(2026, 10, 28)), [2026, 2027])
        self.assertEqual(gp.select_years(years, date(2027, 1, 1)), [2027])
        self.assertEqual(gp.select_years(years, date(2028, 1, 1)), [])

    def test_render_site_generates_no_page_for_past_year(self):
        files = gp.render_site(gp.load_years(), date(2027, 1, 1), lastmod="2027-01-01")
        self.assertTrue(any(p.startswith("2027/") for p in files))
        self.assertFalse(any(p.startswith("2026/") for p in files))
        self.assertFalse(any(p.startswith("2025/") for p in files))
        self.assertNotIn("/2026/", files["sitemap.xml"])


class GeneratedPages(unittest.TestCase):
    """針對 render_site 的輸出做結構檢查（不寫檔）。"""

    @classmethod
    def setUpClass(cls):
        cls.files = gp.render_site(gp.load_years(), date(2026, 10, 28), lastmod="2026-10-28")
        cls.pages = {p: c for p, c in cls.files.items() if p.endswith(".html")}

    def test_every_json_ld_block_parses(self):
        for path, content in self.pages.items():
            blocks = re.findall(r'<script type="application/ld\+json">\n(.*?)\n</script>', content, re.S)
            self.assertGreaterEqual(len(blocks), 2, path)  # BreadcrumbList + FAQPage 至少兩個
            types = []
            for b in blocks:
                obj = json.loads(b)
                types.append(obj["@type"])
            self.assertIn("BreadcrumbList", types, path)
            self.assertIn("FAQPage", types, path)
            if re.fullmatch(r"\d{4}/index\.html", path):
                self.assertIn("Dataset", types, path)

    def test_titles_and_descriptions_unique(self):
        titles = [re.search(r"<title>(.*?)</title>", c).group(1) for c in self.pages.values()]
        descs = [re.search(r'<meta name="description" content="(.*?)">', c).group(1) for c in self.pages.values()]
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual(len(descs), len(set(descs)))

    def test_single_h1_lang_canonical_skip_link(self):
        for path, content in self.pages.items():
            self.assertEqual(content.count("<h1>"), 1, path)
            self.assertIn('<html lang="zh-TW">', content, path)
            self.assertIn(f'<link rel="canonical" href="{gp.SITE}/{path[:-len("index.html")]}">', content, path)
            self.assertIn('class="skip-link"', content, path)
            self.assertIn(f"gtag/js?id={gp.GA_ID}", content, path)

    def test_internal_links_resolve(self):
        root = gp.ROOT
        for path, content in self.pages.items():
            for href in re.findall(r'href="(/[^"#?]*)', content):
                target = root / href.lstrip("/")
                if href.endswith("/"):
                    ok = (target / "index.html").is_file() or f"{href.strip('/')}/index.html" in self.files or href == "/"
                else:
                    ok = target.is_file()
                self.assertTrue(ok, f"{path}: 連結 {href} 不存在")

    def test_sitemap_lists_every_page_and_keeps_root_entries(self):
        sm = self.files["sitemap.xml"]
        self.assertIn(f"<loc>{gp.SITE}/</loc>", sm)
        self.assertIn(f"<loc>{gp.SITE}/api.html</loc>", sm)
        for p in self.pages:
            self.assertIn(f"<loc>{gp.SITE}/{p[:-len('index.html')]}</loc>", sm)
        self.assertNotIn("llms", sm)
        self.assertNotIn(".json", sm)


if __name__ == "__main__":
    unittest.main(verbosity=2)
