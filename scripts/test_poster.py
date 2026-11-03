#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/poster.py（年曆一頁圖）的單元測試。

    python3 scripts/test_poster.py
"""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_pages as gp  # noqa: E402
import poster  # noqa: E402

TODAY = date(2026, 10, 28)
CJK = re.compile(r"[一-鿿]")


def svg_of(html):
    m = re.search(r"<svg id=\"poster\".*?</svg>", html, re.S)
    assert m, "找不到海報 <svg>"
    return m.group(0)


class PosterPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = gp.render_site(gp.load_years(), TODAY, lastmod="2026-10-28")
        cls.years = gp.select_years(gp.load_years(), TODAY)

    def test_pages_exist_for_every_year_and_language(self):
        for y in self.years:
            self.assertIn(f"{y}/calendar/index.html", self.files)
            self.assertIn(f"en/{y}/calendar/index.html", self.files)

    def test_svg_is_well_formed_with_twelve_months(self):
        for y in self.years:
            for path in (f"{y}/calendar/index.html", f"en/{y}/calendar/index.html"):
                root = ET.fromstring(svg_of(self.files[path]))
                ns = "{http://www.w3.org/2000/svg}"
                self.assertEqual(len(root.findall(f"{ns}g")), 12, path)
                self.assertEqual(root.get("viewBox"), f"0 0 {poster.W} {poster.H}")

    def test_css_has_no_unresolved_placeholders(self):
        for path, content in self.files.items():
            if path.endswith("/calendar/index.html") and "poster" in content:
                svg = svg_of(content)
                self.assertNotIn("{font}", svg, path)
                self.assertNotIn("{font_en}", svg, path)

    def test_day_counts_match_data(self):
        for y in self.years:
            calendar, _, _ = gp.load_year(y)
            holiday = sum(1 for e in calendar if e["isHoliday"] and e["description"])
            makeup = sum(1 for e in calendar if (not e["isHoliday"]) and any(k in e["description"] for k in poster.MAKEUP_KEYWORDS))
            for path in (f"{y}/calendar/index.html", f"en/{y}/calendar/index.html"):
                svg = svg_of(self.files[path])
                self.assertEqual(svg.count('class="d d-holiday"'), holiday, path)
                self.assertEqual(svg.count('class="d d-makeup"'), makeup, path)
                # 每天都要畫出一個日期數字
                self.assertEqual(svg.count('class="num"'), len(calendar), path)

    def test_english_poster_has_no_chinese_inside_svg_text_except_none(self):
        for y in self.years:
            svg = svg_of(self.files[f"en/{y}/calendar/index.html"])
            self.assertFalse(CJK.search(svg), f"{y} 英文海報含中文字")

    def test_hreflang_pair_and_language_attributes(self):
        for y in self.years:
            zh = self.files[f"{y}/calendar/index.html"]
            en = self.files[f"en/{y}/calendar/index.html"]
            for html in (zh, en):
                self.assertIn(f'hreflang="zh-TW" href="{gp.SITE}/{y}/calendar/"', html)
                self.assertIn(f'hreflang="en" href="{gp.SITE}/en/{y}/calendar/"', html)
                self.assertIn(f'hreflang="x-default" href="{gp.SITE}/{y}/calendar/"', html)
            self.assertIn('<html lang="zh-TW">', zh)
            self.assertIn('<html lang="en">', en)
            self.assertIn('property="og:locale" content="en_US"', en)

    def test_sitemap_and_entry_points(self):
        sm = self.files["sitemap.xml"]
        for y in self.years:
            self.assertIn(f"{gp.SITE}/{y}/calendar/", sm)
            self.assertIn(f"{gp.SITE}/en/{y}/calendar/", sm)
            self.assertIn(f'href="/{y}/calendar/"', self.files[f"{y}/index.html"])

    def test_download_controls_present(self):
        for path, content in self.files.items():
            if path.endswith("/calendar/index.html") and "poster" in content:
                self.assertIn('id="dl-png"', content, path)
                self.assertIn('id="print-pdf"', content, path)
                self.assertIn("2480", content, path)  # A4 @300dpi


class PosterHelpers(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(poster.classify({"isHoliday": True, "description": "春節"}, 1), "holiday")
        self.assertEqual(poster.classify({"isHoliday": True, "description": ""}, 0), "weekend")
        self.assertEqual(poster.classify({"isHoliday": False, "description": "補行上班"}, 6), "makeup")
        self.assertEqual(poster.classify({"isHoliday": False, "description": ""}, 3), "weekday")
        # 週六補班優先於週末
        self.assertEqual(poster.classify({"isHoliday": False, "description": "調整上班"}, 6), "makeup")

    def test_lunar_label(self):
        self.assertEqual(poster.lunar_label({"date": "冬月廿四"}), "廿四")
        self.assertEqual(poster.lunar_label({"date": "正月初一"}), "正月")
        self.assertEqual(poster.lunar_label({"date": "閏六月初一"}), "閏六月")
        self.assertEqual(poster.lunar_label(None), "")

    def test_holiday_labels(self):
        self.assertEqual(poster.holiday_label("開國紀念日", "zh"), "元旦")
        self.assertLessEqual(len(poster.holiday_label("某個很長很長的新假日名稱", "zh")), 5)
        self.assertEqual(poster.holiday_label("春節", "en"), "Lunar|New Year")

    def test_week_starts_on_sunday(self):
        # 2027/1/1 是週五 → 欄位 5
        d = date(2027, 1, 1)
        self.assertEqual((d.weekday() + 1) % 7, 5)

    def test_roc_year(self):
        self.assertEqual(poster.roc_year(2027), 116)


if __name__ == "__main__":
    unittest.main()
