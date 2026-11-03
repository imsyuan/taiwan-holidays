#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""從 data/ 產生靜態 SEO／AEO 落地頁與 sitemap.xml。

首頁是 JavaScript 渲染的互動行事曆，搜尋引擎與 AI 答題引擎抓不到內容；
本腳本改用純靜態 HTML 把「某年國定假日、連假、補班日、請假攻略」寫成可直接被引用的頁面。

只使用標準函式庫。產出（以 data/years.json 中「今年（含）以後」的年度為準）：

    <year>/index.html           年度總覽：連假、假期表、補班日、請假攻略、FAQ、API 連結
    <year>/<slug>/index.html    每個 3 天以上的連假一頁：日期、請假方案、逐日表、前後連假、FAQ
    calendar/index.html         日曆訂閱說明頁（.ics 本身由 scripts/generate_ics.py 產生）
    sitemap.xml                 重新產生（保留 / 與 /api、加入 /calendar/）
    index.html                  只重寫 <!-- pages:begin/end --> 內鏈區塊（頁尾與 <noscript>），其餘手寫內容不動

請假方案的演算法移植自 mcp/src/engine/index.ts 的 optimizeLeave（bridgePlans），
頁面上的方案與 MCP 工具回傳完全一致；parity 測試見 scripts/test_generate_pages.py。

用法：
    python3 scripts/generate_pages.py            # 產生／更新頁面與 sitemap.xml
    python3 scripts/generate_pages.py --check    # 只檢查是否過期，過期則以非零碼結束
"""

import html
import json
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import en_pages
import poster

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

SITE = "https://tw-holidays.gooliya.com"
SITE_NAME = "Taiwan Holidays"
CDN = "https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data"
GITHUB = "https://github.com/imsyuan/taiwan-holidays"
MCP_ENDPOINT = "https://mcp.tw-holidays.gooliya.com/mcp"
MCP_DOCS = f"{GITHUB}/blob/main/mcp/README.md"
DATA_SOURCE_URL = "https://data.gov.tw/dataset/14718"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
OG_IMAGE = f"{SITE}/img/og-image-v2.png"
GA_ID = "G-XRPQC1GM0S"
STATIC_CSS = "/static.css?v=2"
GENERATED_MARK = "<!-- generated-by: scripts/generate_pages.py -->"

# 首頁 index.html 內由本腳本維護的區塊（標記之間的內容會被整段重寫，標記本身保留）。
PAGES_BLOCK = ("<!-- pages:begin -->", "<!-- pages:end -->")
PAGES_NOSCRIPT_BLOCK = ("<!-- pages-noscript:begin -->", "<!-- pages-noscript:end -->")

# 線上 /api.html 會 307 轉到 /api（Cloudflare 靜態資源預設去掉 .html），所以 canonical／sitemap 用 /api。
API_PATH = "/api"
ICS_PATH = "/calendar/tw-holidays.ics"
ICS_URL = f"{SITE}{ICS_PATH}"
WEBCAL_URL = "webcal://tw-holidays.gooliya.com" + ICS_PATH

# 年度規則：只產生「今年（含）以後」的年度。
#   MIN_YEAR_OFFSET = 0  → 今年起；改成 -1 就會連去年一起產生。
MIN_YEAR_OFFSET = 0

# 連假定義：連續放假（isHoliday=true，含週末）>= MIN_RUN_DAYS 天，不跨年度計算。
MIN_RUN_DAYS = 3

# 請假方案：等同呼叫 MCP optimize_leave(year, annualLeaveDays=LEAVE_BUDGET)。
LEAVE_BUDGET = 5
PLANS_PER_RUN = 3
HUB_EXTRA_PLANS = 5

# 與 mcp/src/engine/index.ts 相同的補班關鍵字；下列描述不能拿來當連假名稱。
MAKEUP_KEYWORDS = ("調整上班", "補行上班", "補班")
NON_NAME_KEYWORDS = ("補假", "調整放假", "彈性放假")

# 連假命名優先序（由高到低）：春節＞清明＞端午＞中秋＞國慶＞元旦＞其他。
# (slug, 顯示名稱, 別名（可為 None，會出現在標題補充搜尋詞）, 資料中會出現的關鍵字)
HOLIDAY_GROUPS = [
    ("lunar-new-year", "春節", "農曆新年", ("春節", "農曆除夕", "小年夜")),
    ("tomb-sweeping", "清明", "清明節、兒童節", ("清明節", "民族掃墓節", "兒童節")),
    ("dragon-boat", "端午", "端午節", ("端午節",)),
    ("mid-autumn", "中秋", "中秋節", ("中秋節",)),
    ("national-day", "國慶", "雙十節", ("國慶日",)),
    ("new-year", "元旦", "開國紀念日", ("開國紀念日", "元旦")),
    ("peace-memorial-day", "二二八和平紀念日", "228 連假", ("和平紀念日",)),
    ("labor-day", "勞動節", "五一勞動節", ("勞動節",)),
    ("teachers-day", "教師節", "孔子誕辰紀念日", ("教師節", "孔子誕辰紀念日")),
    ("taiwan-retrocession-day", "光復節", "臺灣光復節", ("光復",)),
    ("constitution-day", "行憲紀念日", "聖誕節", ("行憲紀念日",)),
]

WEEK_CHARS = "一二三四五六日"  # date.weekday(): 0=一 … 6=日


# ---------------------------------------------------------------------------
# 基本工具
# ---------------------------------------------------------------------------

def esc(text):
    return html.escape(str(text), quote=True)


def parse_compact(compact):
    return date(int(compact[:4]), int(compact[4:6]), int(compact[6:8]))


def compact_to_iso(compact):
    return f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}"


def iso_to_date(iso):
    return date(int(iso[:4]), int(iso[5:7]), int(iso[8:10]))


def wk(d):
    return WEEK_CHARS[d.weekday()]


def md(d):
    return f"{d.month}/{d.day}"


def mdw(d):
    return f"{d.month}/{d.day}（{wk(d)}）"


def long_date(d):
    return f"{d.month} 月 {d.day} 日（週{wk(d)}）"


def time_tag(d, text=None):
    return f'<time datetime="{d.isoformat()}">{esc(text if text is not None else mdw(d))}</time>'


def date_span(start, end):
    return f"{md(start)}–{md(end)}"


def join_dates(dates):
    return "、".join(mdw(d) for d in dates)


def json_ld(obj):
    """以 <script type=application/ld+json> 輸出；把 </ 轉義避免提早關閉 script。"""
    text = json.dumps(obj, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{text}\n</script>'


# ---------------------------------------------------------------------------
# 資料讀取
# ---------------------------------------------------------------------------

def load_years():
    with open(DATA_DIR / "years.json", encoding="utf-8") as f:
        return sorted(int(y) for y in json.load(f)["years"])


def load_year(year):
    with open(DATA_DIR / f"{year}.json", encoding="utf-8") as f:
        calendar = json.load(f)
    with open(DATA_DIR / str(year) / "holidays.json", encoding="utf-8") as f:
        holidays = json.load(f)
    with open(DATA_DIR / str(year) / "makeup-workdays.json", encoding="utf-8") as f:
        makeup = json.load(f)
    calendar.sort(key=lambda e: e["date"])
    return calendar, holidays, makeup


def select_years(all_years, today):
    """年度規則：回傳 >= (今年 + MIN_YEAR_OFFSET) 的年度，升冪。"""
    min_year = today.year + MIN_YEAR_OFFSET
    return [y for y in sorted(all_years) if y >= min_year]


# ---------------------------------------------------------------------------
# 請假引擎（移植自 mcp/src/engine/index.ts；輸出必須與 TS 版逐字相同）
# ---------------------------------------------------------------------------

def is_makeup_workday(day):
    return (not day["isHoliday"]) and any(k in day["description"] for k in MAKEUP_KEYWORDS)


def off_runs(days):
    """連續放假（isHoliday=true）的最大區段，回傳 (start_idx, end_idx) 列表。"""
    runs = []
    i = 0
    n = len(days)
    while i < n:
        if days[i]["isHoliday"]:
            start = i
            while i < n and days[i]["isHoliday"]:
                i += 1
            runs.append((start, i - 1))
        else:
            i += 1
    return runs


def bridge_plans(days, annual_leave_days):
    """相鄰兩段放假之間的上班日若 <= 預算，全請掉就能把兩段接成一段。"""
    runs = off_runs(days)
    plans = []
    for r in range(len(runs) - 1):
        left_start, left_end = runs[r]
        right_start, right_end = runs[r + 1]
        gap = right_start - left_end - 1
        if gap < 1 or gap > annual_leave_days:
            continue
        leave_dates = [compact_to_iso(days[i]["date"]) for i in range(left_end + 1, right_start)]
        total = right_end - left_start + 1
        plans.append({
            "leaveDates": leave_dates,
            "offRange": {
                "start": compact_to_iso(days[left_start]["date"]),
                "end": compact_to_iso(days[right_end]["date"]),
            },
            "totalDaysOff": total,
            "leaveSpent": gap,
            "efficiency": total / gap,
        })
    # TS: b.efficiency - a.efficiency || b.totalDaysOff - a.totalDaysOff || a.start.localeCompare(b.start)
    plans.sort(key=lambda p: (-p["efficiency"], -p["totalDaysOff"], p["offRange"]["start"]))
    return plans


def optimize_leave(calendar, annual_leave_days):
    """等同 MCP optimize_leave（不帶 range）：整年所有可「橋接」的請假方案，依效率排序。"""
    if not isinstance(annual_leave_days, int) or annual_leave_days < 1:
        raise ValueError("annual_leave_days must be a positive integer")
    days = sorted(calendar, key=lambda d: d["date"])
    return bridge_plans(days, annual_leave_days)


# ---------------------------------------------------------------------------
# 連假（run）與命名
# ---------------------------------------------------------------------------

def is_nameable(description):
    return bool(description) and not any(k in description for k in NON_NAME_KEYWORDS)


def classify_run(entries):
    """依優先序決定連假的 slug 與名稱；找不到具名假日時回傳 fallback。"""
    names = [e["description"] for e in entries if is_nameable(e["description"])]
    for slug, label, alias, keywords in HOLIDAY_GROUPS:
        if any(k in n for n in names for k in keywords):
            return slug, label, alias
    start = parse_compact(entries[0]["date"])
    return f"holiday-{start.month:02d}{start.day:02d}", f"{start.month}/{start.day} 起", None


def unique_slugs(slugs):
    """同一年內 slug 重複時加 -2、-3 …。"""
    seen = {}
    out = []
    for s in slugs:
        seen[s] = seen.get(s, 0) + 1
        out.append(s if seen[s] == 1 else f"{s}-{seen[s]}")
    return out


def find_runs(calendar, min_days=MIN_RUN_DAYS):
    """年度內 >= min_days 的連續放假區段，附 slug／名稱（slug 在年內唯一）。"""
    days = sorted(calendar, key=lambda d: d["date"])
    runs = []
    for s, e in off_runs(days):
        if e - s + 1 < min_days:
            continue
        entries = days[s:e + 1]
        slug, label, alias = classify_run(entries)
        holiday_names = []
        for en in entries:
            if en["description"] and en["description"] not in holiday_names:
                holiday_names.append(en["description"])
        runs.append({
            "start": parse_compact(entries[0]["date"]),
            "end": parse_compact(entries[-1]["date"]),
            "length": len(entries),
            "entries": entries,
            "slug": slug,
            "label": label,
            "alias": alias,
            "name": f"{label}連假",
            "holiday_names": holiday_names,
            "weekend_days": sum(1 for en in entries if parse_compact(en["date"]).weekday() >= 5),
            "buja_days": sum(1 for en in entries if en["description"] == "補假"),
        })
    for run, slug in zip(runs, unique_slugs([r["slug"] for r in runs])):
        run["slug"] = slug
    return runs


def plans_for_run(run, year_plans):
    """包含整段連假的引擎方案（最多左右各一），維持引擎排序。"""
    s, e = run["start"].isoformat(), run["end"].isoformat()
    return [p for p in year_plans if p["offRange"]["start"] <= s and p["offRange"]["end"] >= e][:PLANS_PER_RUN]


def combined_plan(run, plans):
    """方案一＋方案二（連假前後都請）合併後的結果；兩側方案都存在時才有。"""
    s, e = run["start"].isoformat(), run["end"].isoformat()
    left = next((p for p in plans if p["offRange"]["start"] < s and p["offRange"]["end"] == e), None)
    right = next((p for p in plans if p["offRange"]["start"] == s and p["offRange"]["end"] > e), None)
    if not left or not right:
        return None
    leave = left["leaveDates"] + right["leaveDates"]
    start, end = left["offRange"]["start"], right["offRange"]["end"]
    total = (iso_to_date(end) - iso_to_date(start)).days + 1
    return {
        "leaveDates": leave,
        "offRange": {"start": start, "end": end},
        "totalDaysOff": total,
        "leaveSpent": len(leave),
        "efficiency": total / len(leave),
        "combined": True,
    }


# ---------------------------------------------------------------------------
# 年度模型
# ---------------------------------------------------------------------------

def build_year(year, all_years_loaded):
    calendar, holidays, makeup = all_years_loaded[year]
    runs = find_runs(calendar)
    plans = optimize_leave(calendar, LEAVE_BUDGET)
    run_lookup = {}
    for run in runs:
        d = run["start"]
        while d <= run["end"]:
            run_lookup[d] = run
            d += timedelta(days=1)
        run["plans"] = plans_for_run(run, plans)
        run["combo"] = combined_plan(run, run["plans"])
    # 沒有接在 3 天以上連假的方案（例如週三的單日假期）
    covered = set()
    for run in runs:
        for p in run["plans"]:
            covered.add((p["offRange"]["start"], p["offRange"]["end"]))
    extra_plans = [p for p in plans if (p["offRange"]["start"], p["offRange"]["end"]) not in covered
                   and p["efficiency"] >= 2][:HUB_EXTRA_PLANS]

    off_days = sum(1 for e in calendar if e["isHoliday"])
    by_date = {parse_compact(e["date"]): e for e in calendar}
    off_len = {}
    for s, e in off_runs(calendar):
        for i in range(s, e + 1):
            off_len[parse_compact(calendar[i]["date"])] = e - s + 1
    longest = max(runs, key=lambda r: (r["length"], -r["start"].toordinal())) if runs else None
    return {
        "year": year,
        "calendar": calendar,
        "by_date": by_date,
        "holidays": holidays,
        "makeup": makeup,
        "makeup_dates": [parse_compact(e["date"]) for e in makeup],
        "runs": runs,
        "run_lookup": run_lookup,
        "off_len": off_len,
        "plans": plans,
        "extra_plans": extra_plans,
        "longest": longest,
        "total_days": len(calendar),
        "off_days": off_days,
        "work_days": len(calendar) - off_days,
        "buja_count": sum(1 for h in holidays if h["description"] == "補假"),
        "weekend_holiday_count": sum(1 for h in holidays if parse_compact(h["date"]).weekday() >= 5
                                     and h["description"] != "補假"),
        "leads_into_next_year": bool(calendar) and calendar[-1]["isHoliday"]
                                and parse_compact(calendar[-1]["date"]).weekday() < 5,
        "flex_holiday_count": sum(1 for e in calendar if "彈性放假" in e["description"]),
    }


def no_makeup_since(all_years_loaded):
    """資料中「從哪一年起之後每年補班日都是 0」；沒有這種年度時回傳 None。"""
    years = sorted(all_years_loaded)
    since = None
    for y in reversed(years):
        if all_years_loaded[y][2]:
            break
        since = y
    return since


# ---------------------------------------------------------------------------
# HTML 片段
# ---------------------------------------------------------------------------

def page_head(title, description, canonical, og_type, extra_ld, extra_head="", lang="zh-TW", locale="zh_TW"):
    ga = f"""    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag() {{ dataLayer.push(arguments); }}
        gtag('js', new Date());
        gtag('config', '{GA_ID}');
    </script>"""
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {GENERATED_MARK}
{ga}
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}">
    <link rel="icon" type="image/png" href="/img/favicon.png">
    <link rel="canonical" href="{esc(canonical)}">
    <meta property="og:type" content="{og_type}">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta property="og:locale" content="{locale}">
    <meta property="og:url" content="{esc(canonical)}">
    <meta property="og:title" content="{esc(title)}">
    <meta property="og:description" content="{esc(description)}">
    <meta property="og:image" content="{OG_IMAGE}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="{esc(canonical)}">
    <meta name="twitter:title" content="{esc(title)}">
    <meta name="twitter:description" content="{esc(description)}">
    <meta name="twitter:image" content="{OG_IMAGE}">
    <meta name="theme-color" content="#F8FAFC" media="(prefers-color-scheme: light)">
    <meta name="theme-color" content="#0B1220" media="(prefers-color-scheme: dark)">
    <link rel="stylesheet" href="{STATIC_CSS}">
{extra_head}{extra_ld}
</head>
"""


def site_header(years, current_year=None, en_href="/en/"):
    links = ['<a href="/">互動行事曆</a>']
    for y in years:
        cur = ' aria-current="page"' if y == current_year else ""
        links.append(f'<a href="/{y}/"{cur}>{y} 年</a>')
    links.append('<a href="/api.html">JSON API</a>')
    links.append(f'<a href="{en_href}" hreflang="en">EN</a>')
    return f"""<body>
    <a class="skip-link" href="#main">跳到主要內容</a>
    <header class="site-header">
        <div class="container">
            <a class="brand" href="/">{SITE_NAME}<span>台灣國定假日行事曆</span></a>
            <nav class="site-nav" aria-label="網站導覽">{''.join(links)}</nav>
        </div>
    </header>
    <main id="main" class="container">
"""


def site_footer():
    return f"""    </main>
    <footer class="site-footer container">
        <p>資料來源：<a href="{DATA_SOURCE_URL}" rel="noopener noreferrer">政府資料開放平台／行政院人事行政總處「中華民國政府行政機關辦公日曆表」</a>（資料集 14718），每月自動同步；以政府最終公告為準。</p>
        <p>資料以 <a href="{LICENSE_URL}" rel="noopener noreferrer">CC BY 4.0</a> 釋出、程式碼採 MIT License。原始碼與資料產生腳本：<a href="{GITHUB}" rel="noopener noreferrer">GitHub imsyuan/taiwan-holidays</a>。本頁由 <code>scripts/generate_pages.py</code> 從 <code>data/</code> 自動產生，不含人工維護的數字。</p>
    </footer>
</body>
</html>
"""


def breadcrumb_html(items):
    lis = []
    for i, (name, href) in enumerate(items):
        if i == len(items) - 1 or not href:
            lis.append(f'<li aria-current="page">{esc(name)}</li>')
        else:
            lis.append(f'<li><a href="{esc(href)}">{esc(name)}</a></li>')
    return f'<nav class="breadcrumb" aria-label="麵包屑"><ol>{"".join(lis)}</ol></nav>'


def breadcrumb_ld(items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    }


def faq_ld(faqs):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs
        ],
    }


def faq_html(faqs):
    parts = ['<section class="card faq" aria-labelledby="faq-h"><h2 id="faq-h">常見問題</h2>']
    for q, a in faqs:
        parts.append(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>")
    parts.append("</section>")
    return "\n".join(parts)


def run_url(year, run):
    return f"/{year}/{run['slug']}/"


def plan_sentence(plan):
    """「請 2 天（2/11（四）、2/12（五）），可從 2/4（四）連休到 2/14（日），共 11 天」"""
    leave = [iso_to_date(x) for x in plan["leaveDates"]]
    s, e = iso_to_date(plan["offRange"]["start"]), iso_to_date(plan["offRange"]["end"])
    return (f"請 {plan['leaveSpent']} 天（{join_dates(leave)}），"
            f"可從 {mdw(s)} 連休到 {mdw(e)}，共 {plan['totalDaysOff']} 天")


def plan_html(index, plan, run_name):
    leave = [iso_to_date(x) for x in plan["leaveDates"]]
    s, e = iso_to_date(plan["offRange"]["start"]), iso_to_date(plan["offRange"]["end"])
    combo = plan.get("combined")
    title = f"方案{'一二三四五'[index]}" + ("（方案一＋方案二合併，連假前後都請）" if combo else "")
    eff = f"{round(plan['efficiency'], 2):g}"
    return f"""<article class="plan{' combo' if combo else ''}">
<h3>{esc(title)}</h3>
<p class="plan-summary">請 <b>{plan['leaveSpent']}</b> 天，連休 <b>{plan['totalDaysOff']}</b> 天（每請 1 天假換到 {eff} 天假期）</p>
<p>請假日期：{"、".join(time_tag(d) for d in leave)}</p>
<p>連休區間：{time_tag(s)} 至 {time_tag(e)}，共 {plan['totalDaysOff']} 天：{len(leave)} 天請假，其餘 {plan['totalDaysOff'] - len(leave)} 天是{esc(run_name)}、週末或其他放假日。</p>
</article>"""


# ---------------------------------------------------------------------------
# 年度總覽頁
# ---------------------------------------------------------------------------

def makeup_sentence(ym, since):
    y = ym["year"]
    if ym["makeup"]:
        dates = "、".join(mdw(d) for d in ym["makeup_dates"])
        return (f"{y} 年有 {len(ym['makeup'])} 天補班日：{dates}。補班日是上班日，"
                f"計算連假與請假時都視為工作日。")
    text = f"{y} 年沒有任何補班日。"
    if since is not None and since <= y:
        if since < y:
            text += f"依本站資料，{since} 年起政府公告的辦公日曆都沒有補班日，"
        else:
            text += f"依本站資料，{y} 年起政府公告的辦公日曆不再有補班日，"
        text += "國定假日遇上週六、週日時改以「補假」處理"
        if ym["flex_holiday_count"] == 0:
            text += "，也沒有過去那種需要週六補班的「彈性放假」"
        text += "。"
    return text


def hub_faqs(ym, since):
    y = ym["year"]
    runs = ym["runs"]
    faqs = []
    faqs.append((
        f"{y} 年台灣有幾天國定假日？",
        f"依政府公告的辦公日曆，{y} 年有 {len(ym['holidays'])} 筆放假紀錄（含 {ym['buja_count']} 天補假，"
        f"以及 {ym['weekend_holiday_count']} 個落在週六、週日的假日），全年 {ym['total_days']} 天中放假 "
        f"{ym['off_days']} 天（含週末）、上班 {ym['work_days']} 天。",
    ))
    lny = next((r for r in runs if r["slug"].startswith("lunar-new-year")), None)
    if lny:
        faqs.append((
            f"{y} 年春節連假是哪幾天？",
            f"{y} 年春節連假從 {long_date(lny['start'])} 放到 {long_date(lny['end'])}，連續 {lny['length']} 天，"
            f"包含{'、'.join(lny['holiday_names'])}" + (f"與 {lny['weekend_days']} 天週末" if lny["weekend_days"] else "") + "。",
        ))
    if ym["longest"]:
        lg = ym["longest"]
        faqs.append((
            f"{y} 年最長的連假是哪一段？",
            f"{y} 年最長的連假是{lg['name']}：{long_date(lg['start'])} 至 {long_date(lg['end'])}，共 {lg['length']} 天。"
            + (f"若在前後請 {lg['combo']['leaveSpent']} 天假，最長可連休 {lg['combo']['totalDaysOff']} 天。" if lg.get("combo") else ""),
        ))
    faqs.append((f"{y} 年有補班日嗎？", makeup_sentence(ym, since)))
    if ym["plans"]:
        best = ym["plans"][0]
        host = ym["run_lookup"].get(iso_to_date(best["offRange"]["start"])) or ym["run_lookup"].get(iso_to_date(best["offRange"]["end"]))
        host_text = f"接在{host['name']}前後，" if host else ""
        a = f"{y} 年最划算的請法是{host_text}{plan_sentence(best)}。"
        if len(ym["plans"]) > 1:
            a += f"次佳方案：{plan_sentence(ym['plans'][1])}。"
        faqs.append((f"{y} 年請哪幾天假最划算？", a))
    if runs:
        faqs.append((
            f"{y} 年有幾個 3 天以上的連假？",
            f"{y} 年共有 {len(runs)} 個 3 天以上的連假（含週末）："
            + "、".join(f"{r['name']} {date_span(r['start'], r['end'])}（{r['length']} 天）" for r in runs) + "。",
        ))
    for slug in ("national-day", "tomb-sweeping", "dragon-boat", "mid-autumn"):
        r = next((r for r in runs if r["slug"].startswith(slug)), None)
        if r:
            faqs.append((
                f"{y} 年{r['label']}連假是哪幾天？",
                f"{y} 年{r['name']}是 {long_date(r['start'])} 至 {long_date(r['end'])}，共 {r['length']} 天，"
                f"包含{'、'.join(r['holiday_names'])}。"
                + (f"最佳請法：{plan_sentence(r['plans'][0])}。" if r["plans"] else ""),
            ))
            break
    faqs.append((
        f"{y} 年的國定假日資料從哪裡來？可以用程式讀取嗎？",
        f"資料來自政府資料開放平台的「中華民國政府行政機關辦公日曆表」（行政院人事行政總處，資料集 14718），"
        f"每月自動同步。程式可直接讀取 JSON：{CDN}/{y}/holidays.json（國定假日）、"
        f"{CDN}/{y}/makeup-workdays.json（補班日）、{CDN}/{y}.json（全年逐日）；"
        f"AI agent 可透過 MCP server {MCP_ENDPOINT} 計算工作日與請假方案。",
    ))
    return faqs[:8]


def render_hub(ym, years, all_loaded, since):
    y = ym["year"]
    runs = ym["runs"]
    lg = ym["longest"]
    canonical = f"{SITE}/{y}/"
    title = f"{y} 台灣國定假日・連假與請假攻略｜{SITE_NAME}"
    desc_runs = f"{len(runs)} 個 3 天以上連假" if runs else "沒有 3 天以上的連假"
    desc_long = f"，最長是{lg['name']} {date_span(lg['start'], lg['end'])} 共 {lg['length']} 天" if lg else ""
    desc_makeup = "沒有補班日" if not ym["makeup"] else f"補班 {len(ym['makeup'])} 天"
    description = (f"{y} 年台灣國定假日 {len(ym['holidays'])} 筆放假紀錄、{desc_runs}{desc_long}；"
                   f"{y} 年{desc_makeup}。附全年假期表、每個連假的請假攻略（請幾天、連休幾天）、FAQ 與 JSON API。")

    prev_year = y - 1 if (y - 1) in years else None
    next_year = y + 1 if (y + 1) in years else None

    # ---- 結構化資料 ----
    crumbs = [("首頁", f"{SITE}/"), (f"{y} 年國定假日", canonical)]
    faqs = hub_faqs(ym, since)
    dataset = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"{y} 年台灣國定假日、補班日與連假資料",
        "description": f"{y} 年中華民國政府行政機關辦公日曆：國定假日 {len(ym['holidays'])} 筆、補班日 {len(ym['makeup'])} 筆、全年逐日 isHoliday 標記與農民曆資訊，JSON 格式。",
        "url": canonical,
        "inLanguage": "zh-TW",
        "keywords": [f"{y} 國定假日", f"{y} 連假", f"{y} 補班", f"{y} 行事曆", "台灣 假日 JSON API"],
        "license": LICENSE_URL,
        "temporalCoverage": f"{y}-01-01/{y}-12-31",
        "spatialCoverage": {"@type": "Place", "name": "Taiwan"},
        "creator": {"@type": "Organization", "name": "Gooliya", "url": "https://www.gooliya.com/"},
        "isBasedOn": {"@type": "CreativeWork", "name": "中華民國政府行政機關辦公日曆表（行政院人事行政總處）", "url": DATA_SOURCE_URL},
        "distribution": [
            {"@type": "DataDownload", "name": f"{y} 全年逐日行事曆（中文，含農民曆）", "encodingFormat": "application/json", "contentUrl": f"{CDN}/{y}.json"},
            {"@type": "DataDownload", "name": f"{y} 國定假日", "encodingFormat": "application/json", "contentUrl": f"{CDN}/{y}/holidays.json"},
            {"@type": "DataDownload", "name": f"{y} 補班日", "encodingFormat": "application/json", "contentUrl": f"{CDN}/{y}/makeup-workdays.json"},
            {"@type": "DataDownload", "name": f"{y} 全年逐日行事曆（英文）", "encodingFormat": "application/json", "contentUrl": f"{CDN}/{y}/calendar-en.json"},
            {"@type": "DataDownload", "name": f"{y} 國定假日（英文）", "encodingFormat": "application/json", "contentUrl": f"{CDN}/{y}/holidays-en.json"},
        ],
    }
    ld = "\n".join([json_ld(breadcrumb_ld(crumbs)), json_ld(faq_ld(faqs)), json_ld(dataset)])
    extra_head = (en_pages.alternates(sys.modules[__name__], y)
                  + f'    <link rel="alternate" type="application/json" href="/data/{y}/holidays.json" title="{y} 國定假日 JSON">\n')

    out = [page_head(title, description, canonical, "website", ld, extra_head), site_header(years, y, en_pages.en_path(y))]
    out.append(breadcrumb_html([(n, u.replace(SITE, "")) for n, u in crumbs]))
    out.append(f"<h1>{y} 台灣國定假日、連假與請假攻略</h1>")

    # ---- 總覽 ----
    longest_text = (f"最長的是<a href=\"{run_url(y, lg)}\">{esc(lg['name'])}</a>（{time_tag(lg['start'])} 至 {time_tag(lg['end'])}，連續 {lg['length']} 天）"
                    if lg else "沒有 3 天以上的連假")
    out.append(f"""<p class="lead">{y} 年台灣的辦公日曆共 {ym['total_days']} 天：放假 {ym['off_days']} 天（含週六、週日）、上班 {ym['work_days']} 天。政府公告的放假紀錄有 {len(ym['holidays'])} 筆（含 {ym['buja_count']} 天補假、{ym['weekend_holiday_count']} 個落在週末的假日），3 天以上的連假共 {len(runs)} 個，{longest_text}。{esc(makeup_sentence(ym, since))}</p>""")
    out.append(f"""<div class="stats">
<div class="stat"><b>{len(ym['holidays'])}</b>筆放假紀錄</div>
<div class="stat"><b>{len(runs)}</b>個 3 天以上連假</div>
<div class="stat"><b>{lg['length'] if lg else 0}</b>天最長連假{('（' + esc(lg['label']) + '）') if lg else ''}</div>
<div class="stat"><b>{len(ym['makeup'])}</b>天補班日</div>
<div class="stat"><b>{ym['work_days']}</b>天上班日</div>
</div>""")
    out.append(f'<p class="note">想要一張可以印出來或存成圖的全年行事曆？<a href="{poster.poster_path(y, "zh")}" target="_blank" rel="noopener">{y} 年曆一頁圖（A4，可下載 PNG／PDF）</a>・<a href="{poster.poster_path(y, "en")}" target="_blank" rel="noopener" hreflang="en">English</a></p>')

    # ---- 連假列表 ----
    if runs:
        items = []
        for r in runs:
            items.append(f'<li><a class="run-name" href="{run_url(y, r)}">{esc(r["name"])}</a>'
                         f'<span class="run-days">{r["length"]} 天</span>'
                         f'<span class="run-dates">{time_tag(r["start"])} 至 {time_tag(r["end"])}・含{esc("、".join(r["holiday_names"]))}</span></li>')
        trailing = ""
        if ym["leads_into_next_year"]:
            last = parse_compact(ym["calendar"][-1]["date"])
            trailing = f"<p class=\"note\">{time_tag(last)} 的假期會接到 {y + 1} 年初，本頁連假以年度為單位計算，未列入。</p>"
        out.append(f"""<section class="card" aria-labelledby="runs-h">
<h2 id="runs-h">{y} 年連假列表（3 天以上）</h2>
<p>連假指連續放假（含週六、週日）3 天以上的區段；名稱依春節、清明、端午、中秋、國慶、元旦、其他的順序決定，點進去看每個連假的請假方案與逐日表。</p>
<ul class="run-list">
{chr(10).join(items)}
</ul>
{trailing}
</section>""")

    # ---- 假期表 ----
    rows = []
    for h in ym["holidays"]:
        d = parse_compact(h["date"])
        run = ym["run_lookup"].get(d)
        n = ym["off_len"].get(d, 1)
        if run:
            cell = f'<a href="{run_url(y, run)}">{esc(run["name"])}</a>（{run["length"]} 天）'
        elif n >= 2:
            cell = f"連休 {n} 天（接週末）"
        else:
            cell = "單日"
        rows.append(f'<tr><th scope="row">{time_tag(d, d.isoformat())}</th><td>週{esc(h["week"])}</td>'
                    f'<td class="wrap">{esc(h["description"])}</td><td>{cell}</td></tr>')
    out.append(f"""<section class="card" aria-labelledby="holidays-h">
<h2 id="holidays-h">{y} 年國定假日一覽表</h2>
<p>共 {len(ym['holidays'])} 筆放假紀錄，依政府公告的辦公日曆列出（含補假與落在週末的假日；一般週末不列入）。</p>
<div class="table-wrap"><table>
<caption>{y} 年國定假日（日期、星期、假日名稱、所屬連假）</caption>
<thead><tr><th scope="col">日期</th><th scope="col">星期</th><th scope="col">假日名稱</th><th scope="col">連假</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table></div>
</section>""")

    # ---- 補班日 ----
    if ym["makeup"]:
        mrows = "".join(f'<tr><th scope="row">{time_tag(parse_compact(m["date"]), compact_to_iso(m["date"]))}</th><td>週{esc(m["week"])}</td><td class="wrap">{esc(m["description"])}</td></tr>' for m in ym["makeup"])
        mk_body = f"""<div class="table-wrap"><table><caption>{y} 年補班日</caption>
<thead><tr><th scope="col">日期</th><th scope="col">星期</th><th scope="col">說明</th></tr></thead><tbody>{mrows}</tbody></table></div>"""
    else:
        mk_body = f"<p>{esc(makeup_sentence(ym, since))}</p>"
    out.append(f"""<section class="card" aria-labelledby="makeup-h">
<h2 id="makeup-h">{y} 年補班日</h2>
{mk_body}
<p class="note">補班日的機器可讀版本：<code>{CDN}/{y}/makeup-workdays.json</code>（沒有補班時為空陣列 <code>[]</code>）。</p>
</section>""")

    # ---- 請假攻略 ----
    if runs or ym["extra_plans"]:
        prow = []
        for r in runs:
            if not r["plans"]:
                prow.append(f'<tr><th scope="row"><a href="{run_url(y, r)}">{esc(r["name"])}</a></th><td colspan="4">前後的上班日超過 {LEAVE_BUDGET} 天，沒有 {LEAVE_BUDGET} 天內的橋接方案</td></tr>')
                continue
            p = r["plans"][0]
            leave = [iso_to_date(x) for x in p["leaveDates"]]
            s, e = iso_to_date(p["offRange"]["start"]), iso_to_date(p["offRange"]["end"])
            prow.append(f'<tr><th scope="row"><a href="{run_url(y, r)}">{esc(r["name"])}</a></th>'
                        f'<td>{p["leaveSpent"]} 天</td><td>{p["totalDaysOff"]} 天</td>'
                        f'<td>{"、".join(time_tag(d) for d in leave)}</td>'
                        f'<td>{time_tag(s)}–{time_tag(e)}</td></tr>')
        extra = ""
        if ym["extra_plans"]:
            erows = []
            for p in ym["extra_plans"]:
                leave = [iso_to_date(x) for x in p["leaveDates"]]
                s, e = iso_to_date(p["offRange"]["start"]), iso_to_date(p["offRange"]["end"])
                names = []
                d = s
                while d <= e:
                    en = ym["by_date"].get(d)
                    if en and is_nameable(en["description"]) and en["description"] not in names:
                        names.append(en["description"])
                    d += timedelta(days=1)
                erows.append(f'<tr><th scope="row" class="wrap">{esc("、".join(names) or "週末")}</th>'
                             f'<td>{p["leaveSpent"]} 天</td><td>{p["totalDaysOff"]} 天</td>'
                             f'<td>{"、".join(time_tag(d) for d in leave)}</td>'
                             f'<td>{time_tag(s)}–{time_tag(e)}</td></tr>')
            spent = sorted({p["leaveSpent"] for p in ym["extra_plans"]})
            spent_text = f"{spent[0]} 天" if len(spent) == 1 else f"{spent[0]}–{spent[-1]} 天"
            extra = f"""<h3>單日假期也能加碼</h3>
<p>落在週間的單日假期雖然不是 3 天連假，但請 {spent_text}就能接上週末或其他假期：</p>
<div class="table-wrap"><table>
<caption>{y} 年不在 3 天連假內的高效率請假方案</caption>
<thead><tr><th scope="col">假日</th><th scope="col">請假</th><th scope="col">連休</th><th scope="col">請假日期</th><th scope="col">連休區間</th></tr></thead>
<tbody>{chr(10).join(erows)}</tbody></table></div>"""
        out.append(f"""<section class="card" aria-labelledby="leave-h">
<h2 id="leave-h">{y} 年請假攻略：每個連假怎麼請最划算</h2>
<p>方案由本站的工作日計算引擎（與 <a href="{MCP_DOCS}" rel="noopener noreferrer">MCP server</a> 的 <code>optimize_leave</code> 相同演算法）算出：把連假前後最多 {LEAVE_BUDGET} 天的上班日請掉，接上另一段假期。下表是每個連假的最佳方案，完整三種方案在各連假頁。</p>
<div class="table-wrap"><table>
<caption>{y} 年各連假的最佳請假方案</caption>
<thead><tr><th scope="col">連假</th><th scope="col">請假</th><th scope="col">連休</th><th scope="col">請假日期</th><th scope="col">連休區間</th></tr></thead>
<tbody>
{chr(10).join(prow)}
</tbody></table></div>
{extra}
</section>""")

    # ---- FAQ ----
    out.append(faq_html(faqs))

    # ---- API 與資料 ----
    out.append(f"""<section class="card" aria-labelledby="api-h">
<h2 id="api-h">{y} 年資料下載與 API</h2>
<p>所有數字都來自下列 JSON 檔，免費、免金鑰，可直接用程式讀取（日期格式 <code>YYYYMMDD</code>）：</p>
<ul class="link-list">
<li><a href="/data/{y}/holidays.json">holidays.json</a> — {y} 年國定假日（CDN：<code>{CDN}/{y}/holidays.json</code>）</li>
<li><a href="/data/{y}/makeup-workdays.json">makeup-workdays.json</a> — {y} 年補班日（CDN：<code>{CDN}/{y}/makeup-workdays.json</code>）</li>
<li><a href="/data/{y}.json">{y}.json</a> — {y} 年全年逐日行事曆，含 <code>isHoliday</code> 與農民曆（CDN：<code>{CDN}/{y}.json</code>）</li>
<li><a href="/data/{y}/calendar-en.json">calendar-en.json</a>、<a href="/data/{y}/holidays-en.json">holidays-en.json</a> — 英文版</li>
</ul>
<p>想算「N 個工作天後是哪天」「這段期間有幾個工作日」「怎麼請假最划算」？給 AI agent 用的 <a href="{MCP_DOCS}" rel="noopener noreferrer">MCP server</a>（端點 <code>{MCP_ENDPOINT}</code>，Streamable HTTP、免認證）提供 <code>count_workdays</code>、<code>add_workdays</code>、<code>next_makeup_workday</code>、<code>optimize_leave</code>、<code>find_travel_windows</code> 五個工具。</p>
<p>更多：<a href="/calendar/">訂閱行事曆（含補班日）</a>・<a href="/api.html">API 說明文件</a>・<a href="/llms-full.txt">llms-full.txt（給 LLM 的完整說明）</a>・<a href="/">互動式行事曆（含農民曆）</a></p>
</section>""")

    # ---- 前後年度 ----
    prev_link = f'<a href="/{prev_year}/" rel="prev">← {prev_year} 年國定假日與連假</a>' if prev_year else f'<span class="disabled">{y - 1} 年頁面未產生</span>'
    next_link = f'<a href="/{next_year}/" rel="next">{next_year} 年國定假日與連假 →</a>' if next_year else f'<span class="disabled">{y + 1} 年行事曆政府尚未公布</span>'
    out.append(f'<nav class="pager" aria-label="前後年度">{prev_link}{next_link}</nav>')

    out.append(site_footer())
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 連假頁
# ---------------------------------------------------------------------------

def monday_of(d):
    return d - timedelta(days=d.weekday())


def sunday_of(d):
    return d + timedelta(days=6 - d.weekday())


def day_table(ym, run, plan, all_by_date):
    """逐日表：涵蓋連假與方案一的連休區間，向前後補滿整週。"""
    s, e = run["start"], run["end"]
    leave = set()
    if plan:
        s = min(s, iso_to_date(plan["offRange"]["start"]))
        e = max(e, iso_to_date(plan["offRange"]["end"]))
        leave = {iso_to_date(x) for x in plan["leaveDates"]}
    start, end = monday_of(s), sunday_of(e)
    rows = []
    d = start
    while d <= end:
        en = all_by_date.get(d)
        if en is None:
            d += timedelta(days=1)
            continue
        if d in leave:
            status, cls, note = "請假", "is-leave", "方案一"
        elif en["isHoliday"]:
            status, cls = "放假", "is-off"
            note = en["description"] or "週末"
        else:
            status, cls = "上班", ""
            note = en["description"] or ""
        badge = {"放假": "badge-off", "請假": "badge-leave", "上班": "badge-work"}[status]
        rows.append(f'<tr class="{cls}"><th scope="row">{time_tag(d, d.isoformat())}</th><td>週{wk(d)}</td>'
                    f'<td><span class="badge {badge}">{status}</span></td><td class="wrap">{esc(note)}</td></tr>')
        d += timedelta(days=1)
    return start, end, "\n".join(rows)


def run_faqs(ym, run, idx):
    y = ym["year"]
    runs = ym["runs"]
    faqs = []
    faqs.append((
        f"{y} 年{run['name']}是哪幾天？",
        f"{y} 年{run['name']}從 {long_date(run['start'])} 放到 {long_date(run['end'])}，連續 {run['length']} 天，"
        f"其中 {run['weekend_days']} 天是週末、{run['length'] - run['weekend_days']} 天是平日放假（{'、'.join(run['holiday_names'])}）。",
    ))
    all_plans = list(run["plans"]) + ([run["combo"]] if run.get("combo") else [])
    if all_plans:
        best_eff = all_plans[0]
        best_long = max(all_plans, key=lambda p: (p["totalDaysOff"], -p["leaveSpent"]))
        a = f"最省假的請法：{plan_sentence(best_eff)}。"
        if best_long is not best_eff:
            a += f"想休最久：{plan_sentence(best_long)}。"
        faqs.append((f"{y} 年{run['name']}要請幾天假才能連休最久？", a))
    near = [d for d in ym["makeup_dates"] if run["start"] - timedelta(days=14) <= d <= run["end"] + timedelta(days=14)]
    if near:
        a = f"要。{run['name']}前後兩週內有補班日：{join_dates(near)}，當天要上班。"
    elif not ym["makeup"]:
        a = f"不用。{y} 年整年都沒有補班日，{run['name']}前後照常週休，不需要補上班。"
    else:
        a = f"{run['name']}前後兩週內沒有補班日；{y} 年的補班日是 {join_dates(ym['makeup_dates'])}。"
    faqs.append((f"{y} 年{run['name']}前後需要補班嗎？", a))
    if run["buja_days"]:
        faqs.append((
            f"{y} 年{run['name']}為什麼有補假？",
            f"{run['name']}裡有 {run['buja_days']} 天「補假」：{join_dates([parse_compact(e['date']) for e in run['entries'] if e['description'] == '補假'])}。"
            f"政府公告的辦公日曆在國定假日遇上週六、週日時，會在相鄰的上班日補放一天，所以這些補假也是正式放假日。",
        ))
    prev_run = runs[idx - 1] if idx > 0 else None
    next_run = runs[idx + 1] if idx + 1 < len(runs) else None
    if next_run:
        gap = (next_run["start"] - run["end"]).days - 1
        a = f"{run['name']}之後，{y} 年的下一個連假是{next_run['name']}（{long_date(next_run['start'])} 至 {long_date(next_run['end'])}，共 {next_run['length']} 天），中間相隔 {gap} 天。"
    else:
        a = f"{run['name']}是 {y} 年最後一個 3 天以上的連假。"
        if prev_run:
            a += f"上一個是{prev_run['name']}（{date_span(prev_run['start'], prev_run['end'])}，{prev_run['length']} 天）。"
    faqs.append((f"{y} 年{run['name']}之後的下一個連假是什麼時候？", a))
    return faqs


def render_run(ym, run, idx, years, all_by_date):
    y = ym["year"]
    runs = ym["runs"]
    canonical = f"{SITE}{run_url(y, run)}"
    plans = run["plans"]
    combo = run.get("combo")
    shown_plans = list(plans)
    if combo and len(shown_plans) < PLANS_PER_RUN:
        shown_plans.append(combo)
    best = plans[0] if plans else None

    alias = f"（{run['alias']}）" if run.get("alias") else ""
    title = f"{y} {run['name']}{alias} {date_span(run['start'], run['end'])} 共 {run['length']} 天・請假攻略｜{SITE_NAME}"
    desc_plan = f"{plan_sentence(best)}。" if best else f"前後上班日較多，沒有 {LEAVE_BUDGET} 天內的橋接請假方案。"
    description = (f"{y} 年{run['name']}{alias}從 {mdw(run['start'])} 放到 {mdw(run['end'])}，連續 {run['length']} 天"
                   f"（{'、'.join(run['holiday_names'])}）。{desc_plan}附逐日放假表、{len(shown_plans)} 種請假方案與前後連假。")

    crumbs = [("首頁", f"{SITE}/"), (f"{y} 年國定假日", f"{SITE}/{y}/"), (run["name"], canonical)]
    faqs = run_faqs(ym, run, idx)
    ld = "\n".join([json_ld(breadcrumb_ld(crumbs)), json_ld(faq_ld(faqs))])

    out = [page_head(title, description, canonical, "article", ld,
                     extra_head=en_pages.alternates(sys.modules[__name__], y, run["slug"])),
           site_header(years, y, en_pages.en_path(y, run["slug"]))]
    out.append(breadcrumb_html([(n, u.replace(SITE, "")) for n, u in crumbs]))
    out.append(f"<h1>{y} 年{esc(run['name'])}：{long_date(run['start'])} 至 {long_date(run['end'])}，共 {run['length']} 天</h1>")

    longer = sum(1 for r in runs if r["length"] > run["length"])
    same = sum(1 for r in runs if r["length"] == run["length"]) - 1
    if longer == 0:
        rank_text = f"是 {y} 年最長的連假" + (f"（與另外 {same} 個連假並列）" if same else "")
    else:
        rank_text = f"長度在 {y} 年 {len(runs)} 個連假中排第 {longer + 1}" + (f"（與另外 {same} 個連假並列）" if same else "")
    lead_plan = f"最划算的請法：{plan_sentence(best)}。" if best else ""
    out.append(f"""<p class="lead">{y} 年{esc(run['name'])}{esc(alias)}從 {time_tag(run['start'])} 放到 {time_tag(run['end'])}，連續放假 {run['length']} 天（{run['weekend_days']} 天週末＋{run['length'] - run['weekend_days']} 天平日假期：{esc('、'.join(run['holiday_names']))}），{rank_text}。{esc(lead_plan)}</p>""")

    # ---- 連假日期表 ----
    rows = []
    for en in run["entries"]:
        d = parse_compact(en["date"])
        rows.append(f'<tr class="is-off"><th scope="row">{time_tag(d, d.isoformat())}</th><td>週{esc(en["week"])}</td><td class="wrap">{esc(en["description"] or "週末")}</td></tr>')
    out.append(f"""<section class="card" aria-labelledby="dates-h">
<h2 id="dates-h">{y} 年{esc(run['name'])}的每一天</h2>
<div class="table-wrap"><table>
<caption>{esc(run['name'])}放假日期（{date_span(run['start'], run['end'])}，共 {run['length']} 天）</caption>
<thead><tr><th scope="col">日期</th><th scope="col">星期</th><th scope="col">假日</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table></div>
</section>""")

    # ---- 請假方案 ----
    if shown_plans:
        plan_blocks = "\n".join(plan_html(i, p, run["name"]) for i, p in enumerate(shown_plans))
        out.append(f"""<section class="card" aria-labelledby="plans-h">
<h2 id="plans-h">{y} 年{esc(run['name'])}請假攻略：{len(shown_plans)} 種方案</h2>
<p>方案一、二由本站工作日計算引擎（與 MCP <code>optimize_leave</code> 相同）算出：把連假前或後的上班日請掉，接上另一段週末或假期。{'方案三是前後一起請的合併結果。' if combo and len(shown_plans) == PLANS_PER_RUN else ''}</p>
{plan_blocks}
</section>""")
    else:
        out.append(f"""<section class="card" aria-labelledby="plans-h">
<h2 id="plans-h">{y} 年{esc(run['name'])}請假攻略</h2>
<p>{esc(run['name'])}前後的上班日都超過 {LEAVE_BUDGET} 天，{LEAVE_BUDGET} 天內沒有能接上另一段假期的方案；想延長可以直接在連假前或後請假。</p>
</section>""")

    # ---- 逐日表 ----
    t_start, t_end, t_rows = day_table(ym, run, best, all_by_date)
    out.append(f"""<section class="card" aria-labelledby="daily-h">
<h2 id="daily-h">{esc(run['name'])}前後逐日表（{date_span(t_start, t_end)}）</h2>
<p>涵蓋{esc(run['name'])}所在的整週{'與方案一的連休區間' if best else ''}：<span class="badge badge-off">放假</span> 為政府公告的放假日或週末、<span class="badge badge-leave">請假</span> 為方案一建議的請假日、<span class="badge badge-work">上班</span> 為一般上班日。</p>
<div class="table-wrap"><table>
<caption>{date_span(t_start, t_end)} 逐日狀態</caption>
<thead><tr><th scope="col">日期</th><th scope="col">星期</th><th scope="col">狀態</th><th scope="col">說明</th></tr></thead>
<tbody>
{t_rows}
</tbody></table></div>
</section>""")

    # ---- 前後連假 ----
    prev_run = runs[idx - 1] if idx > 0 else None
    next_run = runs[idx + 1] if idx + 1 < len(runs) else None
    prev_link = (f'<a href="{run_url(y, prev_run)}" rel="prev">← {esc(prev_run["name"])} {date_span(prev_run["start"], prev_run["end"])}（{prev_run["length"]} 天）</a>'
                 if prev_run else f'<span class="disabled">{esc(run["name"])}是 {y} 年第一個連假</span>')
    next_link = (f'<a href="{run_url(y, next_run)}" rel="next">{esc(next_run["name"])} {date_span(next_run["start"], next_run["end"])}（{next_run["length"]} 天）→</a>'
                 if next_run else f'<span class="disabled">{esc(run["name"])}是 {y} 年最後一個連假</span>')
    out.append(f"""<section class="card" aria-labelledby="neighbors-h">
<h2 id="neighbors-h">{y} 年前後的連假</h2>
<nav class="pager" aria-label="前後連假">{prev_link}{next_link}</nav>
<p>{y} 年共有 {len(runs)} 個 3 天以上的連假，完整列表、全年假期表與補班日請看 <a href="/{y}/">{y} 年國定假日總覽</a>。</p>
</section>""")

    out.append(faq_html(faqs))

    out.append(f"""<section class="card" aria-labelledby="more-h">
<h2 id="more-h">資料來源與 API</h2>
<ul class="link-list">
<li><a href="/{y}/">{y} 年國定假日、連假與請假攻略總覽</a></li>
<li><a href="/data/{y}/holidays.json">{y} 年國定假日 JSON</a>（CDN：<code>{CDN}/{y}/holidays.json</code>）</li>
<li><a href="/api.html">JSON API 說明</a>・<a href="/llms-full.txt">llms-full.txt</a>・<a href="{MCP_DOCS}" rel="noopener noreferrer">MCP server（AI agent 工作日計算）</a></li>
<li><a href="/">互動式行事曆（含農民曆、英文介面）</a></li>
</ul>
</section>""")

    out.append(site_footer())
    return "\n".join(out)


# ---------------------------------------------------------------------------
# calendar/index.html：日曆訂閱說明頁
# ---------------------------------------------------------------------------

CALENDAR_STYLE = """    <style>
        .subscribe-btn { display: inline-block; padding: 0.75rem 1.25rem; border-radius: var(--radius); background: var(--primary); color: #fff; font-weight: 700; text-decoration: none; }
        .subscribe-btn:hover, .subscribe-btn:focus-visible { filter: brightness(1.1); text-decoration: underline; }
        @media (prefers-color-scheme: dark) { .subscribe-btn { color: #0F172A; } }
        .url-box { display: block; padding: 0.6rem 0.75rem; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface-2); overflow-wrap: anywhere; user-select: all; }
    </style>
"""


def calendar_faqs(first_year, last_year):
    return [
        ("訂閱後行事曆會自動更新嗎？",
         "會。檔案內建每日更新提示，我們每週檢查一次政府公告；新年度公布或政府臨時調整假期後，訂閱中的行事曆會跟著更新。實際多久重新抓一次，由 Google、Apple、Microsoft 各自決定，可能延遲半天到一天以上。"),
        ("補班日也會出現在行事曆嗎？",
         "會。每個補班日是一筆全天事件，標題為「補班：…」，一眼就能分辨。政府該年度沒有公告補班時，就不會有補班事件。"),
        ("訂閱的假日會讓我的行程顯示忙碌嗎？",
         "不會。所有事件都標成「有空」，只是提醒，不會擋住別人排會議的時段；實際顯示方式仍取決於你的行事曆 App。"),
        ("Apple 行事曆跳出不安全提示該怎麼辦？",
         "訂閱時 iPhone 或 Mac 可能提示來源不安全，原因是 webcal:// 這個網址格式本身沒有標示是否加密。本站檔案實際以 HTTPS 提供、內容只有公開的假日資料。想避開提示，可改用手動加入訂閱行事曆，貼上 https:// 開頭的網址；實際跳出的文字依系統版本而異。"),
        ("資料從哪裡來、可以拿去用嗎？",
         f"來源是行政院人事行政總處的「中華民國政府行政機關辦公日曆表」（政府資料開放平台資料集 14718），依政府資料開放授權條款－第 1 版釋出。本站整理後的資料以 CC BY 4.0 提供，引用請標示出處。目前涵蓋 {first_year}–{last_year} 年，以政府最終公告為準。"),
    ]


def render_calendar_page(years, all_years=None):
    """日曆訂閱說明頁。years 供導覽列使用；all_years 決定「涵蓋年度」文字（預設同 years）。"""
    all_years = all_years or years
    first_year, last_year = min(all_years), max(all_years)
    canonical = f"{SITE}/calendar/"
    title = f"訂閱台灣假日行事曆（含補班日 .ics）｜{SITE_NAME}"
    description = ("一鍵把台灣國定假日與補班日加進 Google 日曆、Apple 行事曆、Outlook：訂閱一次，"
                   f"新年度與政府臨時調整都會自動更新。涵蓋 {first_year}–{last_year} 年，免費、免登入。")
    crumbs = [("首頁", f"{SITE}/"), ("訂閱行事曆", canonical)]
    faqs = calendar_faqs(first_year, last_year)
    webpage = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "訂閱台灣假日行事曆（含補班日）",
        "description": description,
        "url": canonical,
        "inLanguage": "zh-TW",
        "license": LICENSE_URL,
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": f"{SITE}/"},
        "isBasedOn": {"@type": "CreativeWork", "name": "中華民國政府行政機關辦公日曆表（行政院人事行政總處）", "url": DATA_SOURCE_URL},
        "about": "台灣國定假日與補班日的 iCalendar（.ics）訂閱行事曆",
    }
    ld = "\n".join([json_ld(breadcrumb_ld(crumbs)), json_ld(faq_ld(faqs)), json_ld(webpage)])
    extra_head = f'    <link rel="alternate" type="text/calendar" href="{ICS_PATH}" title="台灣國定假日與補班日">\n{CALENDAR_STYLE}'

    out = [page_head(title, description, canonical, "website", ld, extra_head), site_header(years)]
    out.append(breadcrumb_html([(n, u.replace(SITE, "")) for n, u in crumbs]))
    out.append("<h1>訂閱台灣假日行事曆（含補班日）</h1>")
    out.append(f"""<p class="lead">把台灣國定假日與補班日一次加進你的 Google 日曆、Apple 行事曆或 Outlook：訂閱一次，之後新年度公布、政府臨時調整假期，行事曆都會自己更新。免費、免登入，涵蓋 {first_year}–{last_year} 年。</p>""")

    out.append(f"""<section class="card" aria-labelledby="subscribe-h">
<h2 id="subscribe-h">一鍵訂閱</h2>
<p><a class="subscribe-btn" href="{WEBCAL_URL}">訂閱台灣假日行事曆</a></p>
<p>點上方按鈕，iPhone、iPad、Mac 與多數桌面行事曆 App 會自動打開並詢問是否訂閱。Google 日曆與 Outlook 網頁版不接受這種網址，請照下面的步驟手動貼上。</p>
<p>訂閱網址（HTTPS，手動貼上時用這個）：</p>
<code class="url-box">{ICS_URL}</code>
<p class="note">只想匯入一次、不要自動更新？可以<a href="{ICS_PATH}" download>下載 .ics 檔</a>，但匯入的內容之後不會跟著更新，通常不建議。</p>
</section>""")

    out.append(f"""<section class="card" aria-labelledby="google-h">
<h2 id="google-h">Google 日曆</h2>
<ol>
<li>用電腦打開 Google 日曆（calendar.google.com）。手機 App 不能新增訂閱，但在電腦加好後，登入同一個帳號的手機會一併顯示。</li>
<li>在左側「其他日曆」旁按「＋」，選「從網址新增」。</li>
<li>貼上 <code>{ICS_URL}</code>，按「新增日曆」。</li>
</ol>
<p class="note">Google 重新抓訂閱日曆的時間由 Google 決定，可能延遲半天到一天以上，無法手動要求立即更新。</p>
</section>""")

    out.append("""<section class="card" aria-labelledby="apple-h">
<h2 id="apple-h">Apple 行事曆（iPhone、iPad、Mac）</h2>
<ol>
<li>最快的方式：在 iPhone、iPad 或 Mac 上點本頁上方的「訂閱台灣假日行事曆」按鈕，再按系統跳出的「訂閱」。</li>
<li>手動加入（iPhone、iPad）：打開齒輪圖示的系統 App，進入「行事曆」→「帳號」→「加入帳號」→「其他」→「加入訂閱行事曆」，貼上 https 網址。</li>
<li>手動加入（Mac）：行事曆 App 的選單列選「檔案」→「新增行事曆訂閱⋯」，貼上 https 網址，更新頻率選「每天」。</li>
</ol>
<p class="note"><strong>Apple 可能顯示不安全提示：</strong>訂閱時系統有時會警告來源不安全，原因是 webcal:// 這個網址格式本身沒有標示是否加密，系統無法事先確認。本站檔案實際以 HTTPS 提供，內容只有公開的假日資料，不含任何個人資料。你可以選「訂閱」繼續；想避開提示，就用上面的手動方式貼 https:// 網址。實際跳出的文字依系統版本而異。</p>
</section>""")

    out.append(f"""<section class="card" aria-labelledby="outlook-h">
<h2 id="outlook-h">Outlook</h2>
<ol>
<li>用瀏覽器打開 Outlook 網頁版（outlook.live.com 或公司的 Microsoft 365 信箱），切到「行事曆」。</li>
<li>按「新增行事曆」，選「從網際網路訂閱」。</li>
<li>貼上 <code>{ICS_URL}</code>，取個名稱（例如「台灣國定假日與補班日」），按「匯入」。</li>
</ol>
<p class="note">傳統桌面版 Outlook 的操作路徑因版本而異，建議先在網頁版訂閱，桌面版登入同一個帳號後會一併顯示。Outlook 重新抓訂閱的間隔由 Microsoft 決定，可能需要數小時到一天以上。</p>
</section>""")

    out.append("""<section class="card" aria-labelledby="content-h">
<h2 id="content-h">訂閱內容</h2>
<ul>
<li><strong>國定假日</strong>：每個放假日一筆全天事件，含補假、調整放假與落在週末的假日；一般週末不列入。</li>
<li><strong>補班日</strong>：每個補班日一筆全天事件，標題為「補班：…」。</li>
<li>事件備註附上本站對應的連假頁或年度頁，可直接點進去看請假攻略。</li>
<li>所有事件都標成「有空」，不會讓你的行程顯示忙碌。</li>
<li>內容由 <code>scripts/generate_ics.py</code> 從 <code>data/</code> 自動產生，與本站 JSON API 是同一份資料。</li>
</ul>
</section>""")

    out.append(faq_html(faqs))

    out.append(f"""<section class="card" aria-labelledby="source-h">
<h2 id="source-h">資料來源與授權</h2>
<p>資料來源：行政院人事行政總處「中華民國政府行政機關辦公日曆表」（<a href="{DATA_SOURCE_URL}" rel="noopener noreferrer">政府資料開放平台資料集 14718</a>），依<a href="https://data.gov.tw/license" rel="noopener noreferrer">政府資料開放授權條款－第 1 版</a>釋出。本站整理後的資料以 <a href="{LICENSE_URL}" rel="noopener noreferrer">CC BY 4.0</a> 提供，引用請標示出處與本站網址。一切以政府最終公告為準。</p>
<p>想用 API 讀取？見 <a href="/api.html">JSON API 說明</a>・<a href="/">互動式行事曆</a>・<a href="/{max(years)}/">{max(years)} 年國定假日與連假</a></p>
</section>""")

    out.append(site_footer())
    return "\n".join(out)


# ---------------------------------------------------------------------------
# index.html 內鏈區塊（<!-- pages:begin/end -->）
# ---------------------------------------------------------------------------

def replace_marked_block(text, markers, body):
    """把 text 中 begin／end 標記之間的內容換成 body（標記保留；沿用 begin 標記行的縮排）。冪等。"""
    begin, end = markers
    i, j = text.find(begin), text.find(end)
    if i < 0 or j < 0 or j < i:
        raise SystemExit(f"index.html 找不到標記 {begin} … {end}")
    line_start = text.rfind("\n", 0, i) + 1
    indent = text[line_start:i]
    if indent.strip():
        indent = ""
    lines = [(indent + ln) if ln else ln for ln in body.split("\n")]
    return text[:i + len(begin)] + "\n" + "\n".join(lines) + "\n" + indent + text[j:]


def render_pages_block(years, runs_by_year):
    """頁尾的「各年度連假頁」：純靜態 <a href>，爬蟲不需要 JavaScript 就看得到。

    畫面上預設只顯示各年度總覽與訂閱連結；各連假頁收進 <details>（內容仍在原始 HTML 裡）。"""
    main = [f'<a href="/{y}/">{y} 年連假總覽</a>' for y in years]
    main.extend(f'<a href="{poster.poster_path(y, "zh")}" target="_blank" rel="noopener">{y} 年曆一頁圖</a>' for y in years)
    main.append('<a href="/calendar/">訂閱行事曆（.ics）</a>')
    main.append('<a href="/en/" hreflang="en">English</a>')
    rows = []
    for y in years:
        links = [f'<a href="{run_url(y, r)}">{esc(r["name"])}</a>' for r in runs_by_year[y]]
        rows.append(f"<p><strong>{y}</strong>\n" + "\n".join(links) + "</p>")
    return ('<nav class="footer-pages" aria-label="各年度連假頁">\n'
            '<p class="footer-pages-main">' + "\n".join(main) + "</p>\n"
            '<details>\n<summary>各連假頁</summary>\n' + "\n".join(rows) + "\n</details>\n</nav>")


def render_pages_noscript(years):
    links = "｜".join(f'<a href="/{y}/">{y} 年連假頁</a>' for y in years)
    return f'<p>各年度連假頁：{links}｜<a href="/calendar/">訂閱行事曆</a></p>'


def render_index_html(text, all_years, today):
    years = select_years(all_years, today)
    runs_by_year = {y: find_runs(load_year(y)[0]) for y in years}
    text = replace_marked_block(text, PAGES_BLOCK, render_pages_block(years, runs_by_year))
    return replace_marked_block(text, PAGES_NOSCRIPT_BLOCK, render_pages_noscript(years))


# ---------------------------------------------------------------------------
# sitemap.xml
# ---------------------------------------------------------------------------

def data_lastmod(years, today):
    """data/ 最後一次變動的日期（git 提交日；有未提交的變動時為今天）；取不到時用今天。"""
    paths = [str(DATA_DIR / "years.json")] + [str(DATA_DIR / f"{y}.json") for y in years] + [str(DATA_DIR / str(y)) for y in years]
    try:
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", *paths],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
        ).stdout.strip()
        if dirty:  # 資料剛更新、尚未提交（Action 流程）：以今天為準，否則 lastmod 會落後一輪
            return today.isoformat()
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", *paths],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
        ).stdout.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", out):
            return out
    except (OSError, subprocess.SubprocessError):
        pass
    return today.isoformat()


def with_alternates(entries):
    """中英文成對的網址（/ ↔ /en/、/<y>/… ↔ /en/<y>/…）互加 xhtml:link alternate。"""
    en_prefix = f"{SITE}/en/"
    zh_of = {}
    for e in entries:
        loc = e[0]
        if loc.startswith(en_prefix):
            zh_of[loc] = f"{SITE}/" + loc[len(en_prefix):]
    by_loc = {e[0] for e in entries}
    out = []
    for e in entries:
        loc = e[0]
        zh = zh_of.get(loc) if loc in zh_of else loc
        en = loc if loc in zh_of else f"{en_prefix}{loc[len(SITE) + 1:]}"
        if zh in by_loc and en in by_loc:
            out.append(tuple(e[:4]) + ([("zh-TW", zh), ("en", en), ("x-default", zh)],))
        else:
            out.append(tuple(e[:4]))
    return out


def render_sitemap(entries):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for entry in entries:
        loc, lastmod, changefreq, priority = entry[:4]
        alts = entry[4] if len(entry) > 4 else ()
        lines.append("  <url>")
        lines.append(f"    <loc>{esc(loc)}</loc>")
        for hl, href in alts:
            lines.append(f'    <xhtml:link rel="alternate" hreflang="{hl}" href="{esc(href)}"/>')
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 組裝
# ---------------------------------------------------------------------------

def render_site(all_years, today, lastmod=None):
    """回傳 {相對路徑: 內容}；不寫檔，方便測試。"""
    years = select_years(all_years, today)
    loaded = {y: load_year(y) for y in all_years}
    since = no_makeup_since(loaded)
    all_by_date = {}
    for y in all_years:
        for e in loaded[y][0]:
            all_by_date[parse_compact(e["date"])] = e

    files = {}
    sitemap = [(f"{SITE}/", lastmod, "weekly", "1.0"), (f"{SITE}{API_PATH}", lastmod, "monthly", "0.8")]
    for y in years:
        ym = build_year(y, loaded)
        files[f"{y}/index.html"] = render_hub(ym, years, loaded, since)
        sitemap.append((f"{SITE}/{y}/", lastmod, "monthly", "0.9"))
        for idx, run in enumerate(ym["runs"]):
            files[f"{y}/{run['slug']}/index.html"] = render_run(ym, run, idx, years, all_by_date)
            sitemap.append((f"{SITE}{run_url(y, run)}", lastmod, "monthly", "0.7"))
    for y in years:
        calendar, holidays, _ = loaded[y]
        for lang in ("zh", "en"):
            files[poster.poster_path(y, lang).strip("/") + "/index.html"] = poster.render_poster_page(
                sys.modules[__name__], y, calendar, holidays, years, lang)
            sitemap.append((f"{SITE}{poster.poster_path(y, lang)}", lastmod, "monthly", "0.7"))
    files["calendar/index.html"] = render_calendar_page(years, all_years)
    sitemap.append((f"{SITE}/calendar/", lastmod, "monthly", "0.6"))
    en_files, en_sitemap = en_pages.render_en_site(sys.modules[__name__], years, loaded, since, all_by_date, lastmod)
    files.update(en_files)
    sitemap.extend(en_sitemap)
    if lastmod is not None:
        files["sitemap.xml"] = render_sitemap(with_alternates(sitemap))
    return files


def prune_stale(years, keep):
    """移除本腳本先前產生、但這次沒再產生的連假子頁。"""
    removed = []
    for y in years:
        for prefix in ("", "en/"):
            ydir = ROOT / (prefix + str(y))
            if not ydir.is_dir():
                continue
            for sub in ydir.iterdir():
                idx = sub / "index.html"
                rel = f"{prefix}{y}/{sub.name}/index.html"
                if sub.is_dir() and idx.is_file() and rel not in keep:
                    try:
                        if GENERATED_MARK in idx.read_text(encoding="utf-8"):
                            shutil.rmtree(sub)
                            removed.append(rel)
                    except OSError:
                        pass
    return removed


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    today = date.today()
    all_years = load_years()
    years = select_years(all_years, today)
    if not years:
        raise SystemExit(f"data/years.json 沒有 >= {today.year + MIN_YEAR_OFFSET} 的年度，無頁面可產生")
    files = render_site(all_years, today, lastmod=data_lastmod(years, today))
    index_path = ROOT / "index.html"
    files["index.html"] = render_index_html(index_path.read_text(encoding="utf-8"), all_years, today)

    stale = []
    for rel, content in files.items():
        path = ROOT / rel
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old != content:
            stale.append(rel)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
    removed = [] if check else prune_stale(years, set(files))

    if check:
        if stale:
            print("以下頁面已過期，請執行 python3 scripts/generate_pages.py：")
            for s in stale:
                print(f"  - {s}")
            sys.exit(1)
        print("靜態頁面已是最新。")
        return
    print(f"年度：{', '.join(str(y) for y in years)}；共 {len(files)} 個檔案，更新 {len(stale)} 個，移除 {len(removed)} 個。")
    for s in stale:
        print(f"  已更新 {s}")
    for r in removed:
        print(f"  已移除 {r}")


if __name__ == "__main__":
    main()
