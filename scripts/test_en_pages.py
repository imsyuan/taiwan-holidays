#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/en_pages.py（英文靜態頁）的單元測試。

    python3 scripts/test_en_pages.py
"""

import re
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import en_pages  # noqa: E402
import generate_pages as gp  # noqa: E402

TODAY = date(2026, 10, 28)
CJK = re.compile(r"[一-鿿]")


def visible_text(html):
    """去掉 <head>、script、style 與標籤後的可見文字。"""
    html = re.sub(r"<head>.*?</head>|<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


class EnglishPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = gp.render_site(gp.load_years(), TODAY, lastmod="2026-10-28")
        cls.years = gp.select_years(gp.load_years(), TODAY)
        cls.en = {p: c for p, c in cls.files.items() if p.startswith("en/") and p.endswith(".html")}

    def test_every_zh_page_has_an_english_counterpart(self):
        for y in self.years:
            self.assertIn(f"en/{y}/index.html", self.files)
            zh_runs = [p for p in self.files if re.fullmatch(rf"{y}/[a-z0-9-]+/index\.html", p) and not p.startswith(f"{y}/calendar/")]
            self.assertTrue(zh_runs)
            for p in zh_runs:
                self.assertIn("en/" + p, self.files, p)
        self.assertIn("en/index.html", self.files)

    def test_english_pages_have_no_chinese_in_visible_text(self):
        for path, html in self.en.items():
            if path.endswith("/calendar/index.html"):
                continue  # 海報頁導覽列的「中文」切換連結是刻意保留的
            text = visible_text(html).replace("中文", "")
            self.assertFalse(CJK.search(text), f"{path} 含中文：{CJK.findall(text)[:5]}")

    def test_hreflang_pairs_are_reciprocal(self):
        for y in self.years:
            for zh_path in (f"{y}/index.html", f"{y}/lunar-new-year/index.html"):
                en_path = "en/" + zh_path
                if en_path not in self.files:
                    continue
                zh_url = f"{gp.SITE}/{zh_path[:-len('index.html')]}"
                en_url = f"{gp.SITE}/{en_path[:-len('index.html')]}"
                for html in (self.files[zh_path], self.files[en_path]):
                    self.assertIn(f'hreflang="zh-TW" href="{zh_url}"', html, zh_path)
                    self.assertIn(f'hreflang="en" href="{en_url}"', html, zh_path)
        home_zh = (gp.ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('hreflang="en" href="https://tw-holidays.gooliya.com/en/"', home_zh)
        self.assertIn('hreflang="zh-TW" href="https://tw-holidays.gooliya.com/"', self.files["en/index.html"])

    def test_numbers_match_the_chinese_pages(self):
        for y in self.years:
            ym = gp.build_year(y, {yy: gp.load_year(yy) for yy in gp.load_years()})
            html = self.files[f"en/{y}/index.html"]
            self.assertIn(f"<b>{len(ym['holidays'])}</b>holiday entries", html)
            self.assertIn(f"<b>{len(ym['runs'])}</b>long weekends", html)
            for r in ym["runs"]:
                page = self.files[f"en/{y}/{r['slug']}/index.html"]
                self.assertIn(f"{r['length']} days", page)
                best = r["plans"][0] if r["plans"] else None
                if best:
                    self.assertIn(f"Take <b>{best['leaveSpent']}</b>", page)
                    self.assertIn(f"<b>{best['totalDaysOff']}</b> days in a row", page)

    def test_sitemap_has_alternates_for_every_pair(self):
        sm = self.files["sitemap.xml"]
        self.assertIn('xmlns:xhtml="http://www.w3.org/1999/xhtml"', sm)
        for path in self.en:
            url = f"{gp.SITE}/{path[:-len('index.html')]}"
            self.assertIn(f"<loc>{url}</loc>", sm, path)
        for y in self.years:
            block = re.search(rf"<url>\s*<loc>{re.escape(gp.SITE)}/{y}/</loc>(.*?)</url>", sm, re.S).group(1)
            self.assertIn(f'hreflang="en" href="{gp.SITE}/en/{y}/"', block)
            self.assertIn('hreflang="x-default"', block)

    def test_titles_and_descriptions_are_unique_across_languages(self):
        titles = [re.search(r"<title>(.*?)</title>", c).group(1) for c in self.files.values() if "<title>" in c]
        self.assertEqual(len(titles), len(set(titles)))

    def test_zh_pages_link_to_english(self):
        self.assertIn('hreflang="en">EN</a>', self.files["2027/index.html"])
        self.assertIn(f'href="/en/2027/lunar-new-year/" hreflang="en">EN', self.files["2027/lunar-new-year/index.html"])


class EnglishHelpers(unittest.TestCase):
    def test_run_names(self):
        self.assertEqual(en_pages.run_en({"slug": "lunar-new-year", "start": date(2027, 2, 4)})[0], "Lunar New Year holiday")
        self.assertEqual(en_pages.run_en({"slug": "dragon-boat-2", "start": date(2027, 6, 9)})[0], "Dragon Boat Festival long weekend (2)")
        self.assertEqual(en_pages.run_en({"slug": "holiday-0305", "start": date(2027, 3, 5)})[0], "Long weekend from Mar 5")

    def test_date_formats(self):
        d = date(2027, 2, 4)
        self.assertEqual(en_pages.mdw(d), "Feb 4 (Thu)")
        self.assertEqual(en_pages.long_date(d), "Thursday, February 4, 2027")
        self.assertEqual(en_pages.span(date(2027, 2, 4), date(2027, 2, 10)), "Feb 4–Feb 10")
        self.assertEqual(en_pages.plural(1, "day"), "1 day")
        self.assertEqual(en_pages.plural(2, "day"), "2 days")


if __name__ == "__main__":
    unittest.main()
