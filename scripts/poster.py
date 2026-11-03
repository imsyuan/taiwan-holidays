#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""年曆一頁圖（A4 直式、12 個月）：<year>/calendar/ 與 en/<year>/calendar/。

版面參考人事行政總處「政府行政機關辦公日曆表」：3 欄 × 4 列、週日起算，
週末與國定假日上色，中文版另標農曆與節氣，補班日加藍框。
圖本身是內嵌 SVG（固定淺底、自帶 <style>），所以能直接：
  - 在頁面上預覽、放大；
  - 按鈕在瀏覽器端轉成 A4 300dpi 的 PNG 下載；
  - 用瀏覽器列印（版面已設 A4）另存 PDF。
不需要在 CI 安裝瀏覽器；資料更新時（generate_pages.py 重跑）圖也跟著更新。

由 scripts/generate_pages.py 呼叫 render_poster_page()；為避免循環匯入，
頁面外框函式（page_head 等）由呼叫端以 gp 參數傳入。
"""

import json
from datetime import date

# ---------------------------------------------------------------------------
# 版面常數（SVG 使用者座標，A4 比例 1 : 1.4143）
# ---------------------------------------------------------------------------

W, H = 2100, 2970
MARGIN = 80
GAP = 28
BLOCK_W = (W - 2 * MARGIN - 2 * GAP) / 3
TOP = 340
BOTTOM = 2790
BLOCK_H = (BOTTOM - TOP - 3 * GAP) / 4
HEAD_H = 84
WEEKDAY_H = 40
ROW_H = (BLOCK_H - HEAD_H - WEEKDAY_H) / 6
CELL_W = BLOCK_W / 7

MAKEUP_KEYWORDS = ("調整上班", "補行上班", "補班")

FONT_ZH = "'PingFang TC','Noto Sans TC','Microsoft JhengHei','Heiti TC','Source Han Sans TC',sans-serif"
FONT_EN = "'Inter','Helvetica Neue','Segoe UI',Roboto,Arial,sans-serif"

ZH_MONTHS = ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December"]
ZH_WEEK = ["日", "一", "二", "三", "四", "五", "六"]
EN_WEEK = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]

# 格子很小，國定假日名稱用縮寫；沒列到的名稱截前 5 個字
ZH_SHORT = {
    "開國紀念日": "元旦",
    "農曆除夕": "除夕",
    "和平紀念日": "和平紀念",
    "兒童節及民族掃墓節": "兒童清明",
    "孔子誕辰紀念日/教師節": "教師節",
    "孔子誕辰紀念日": "教師節",
    "臺灣光復暨金門古寧頭大捷紀念日": "光復節",
    "臺灣光復節": "光復節",
    "行憲紀念日": "行憲紀念",
}

# 英文縮寫用 "|" 分兩行
EN_SHORT = {
    "開國紀念日": "New Year's|Day",
    "小年夜": "Lunar NY|Eve Eve",
    "農曆除夕": "Lunar NY|Eve",
    "春節": "Lunar|New Year",
    "補假": "Day Off",
    "和平紀念日": "Peace|Memorial",
    "兒童節": "Children's|Day",
    "兒童節及民族掃墓節": "Children's &|Tomb Sweep",
    "清明節": "Tomb|Sweeping",
    "民族掃墓節": "Tomb|Sweeping",
    "勞動節": "Labor|Day",
    "端午節": "Dragon|Boat",
    "中秋節": "Mid-|Autumn",
    "國慶日": "National|Day",
    "孔子誕辰紀念日": "Confucius|Birthday",
    "孔子誕辰紀念日/教師節": "Confucius|Birthday",
    "臺灣光復暨金門古寧頭大捷紀念日": "Retrocession|Day",
    "臺灣光復節": "Retrocession|Day",
    "行憲紀念日": "Constitution|Day",
    "調整放假": "Adjusted|Holiday",
    "彈性放假": "Flexible|Holiday",
}

# 英文版國定假日清單（頁面文字內容；比格子縮寫完整）
EN_FULL = {
    "開國紀念日": "New Year's Day",
    "小年夜": "Lunar New Year's Eve Eve",
    "農曆除夕": "Lunar New Year's Eve",
    "春節": "Lunar New Year",
    "補假": "Compensatory Leave",
    "和平紀念日": "Peace Memorial Day",
    "兒童節": "Children's Day",
    "兒童節及民族掃墓節": "Children's Day & Tomb Sweeping Day",
    "清明節": "Tomb Sweeping Day",
    "民族掃墓節": "Tomb Sweeping Day",
    "勞動節": "Labor Day",
    "端午節": "Dragon Boat Festival",
    "中秋節": "Mid-Autumn Festival",
    "國慶日": "National Day",
    "孔子誕辰紀念日": "Confucius Birthday (Teachers' Day)",
    "孔子誕辰紀念日/教師節": "Confucius Birthday (Teachers' Day)",
    "臺灣光復暨金門古寧頭大捷紀念日": "Taiwan Retrocession Day",
    "臺灣光復節": "Taiwan Retrocession Day",
    "行憲紀念日": "Constitution Day",
    "調整放假": "Adjusted Holiday",
    "彈性放假": "Flexible Holiday",
}


def poster_path(year, lang):
    return f"/{year}/calendar/" if lang == "zh" else f"/en/{year}/calendar/"


def en_date(d):
    """Mar 5 (Fri)：不用 strftime，避免受系統 locale 影響。"""
    return f"{EN_MONTHS[d.month - 1][:3]} {d.day} ({['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d.weekday()]})"


def roc_year(year):
    return year - 1911


# ---------------------------------------------------------------------------
# 每日分類
# ---------------------------------------------------------------------------

def classify(day, weekday_idx):
    """回傳 'makeup'、'holiday'、'weekend'、'weekday'。weekday_idx：週日起算 0=日…6=六。"""
    desc = day["description"]
    if (not day["isHoliday"]) and any(k in desc for k in MAKEUP_KEYWORDS):
        return "makeup"
    if day["isHoliday"] and desc:
        return "holiday"
    if weekday_idx in (0, 6):
        return "weekend"
    return "weekday"


def holiday_label(desc, lang):
    """回傳格子裡的名稱（zh：單行字串；en：以 | 分行）。"""
    if lang == "zh":
        short = ZH_SHORT.get(desc, desc)
        return short if len(short) <= 5 else short[:5]
    return EN_SHORT.get(desc, desc.replace(" ", "|", 1) if " " in desc else desc)[:24]


def lunar_label(lunar):
    """農曆日的小字：初一顯示月份（正月、閏六月），其餘顯示日（初二、廿四）。"""
    if not lunar or not lunar.get("date"):
        return ""
    s = lunar["date"]
    return s[:-2] if s.endswith("初一") else s[-2:]


# ---------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------

def _t(esc, x, y, text, cls, extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="middle"{extra}>{esc(text)}</text>'


def render_month(esc, year, month, days_by_date, lang):
    col = (month - 1) % 3
    row = (month - 1) // 3
    bx = MARGIN + col * (BLOCK_W + GAP)
    by = TOP + row * (BLOCK_H + GAP)
    out = [f'<g transform="translate({bx:.1f},{by:.1f})">']
    out.append(f'<rect class="m-card" width="{BLOCK_W:.1f}" height="{BLOCK_H:.1f}" rx="22"/>')
    title = ZH_MONTHS[month - 1] if lang == "zh" else EN_MONTHS[month - 1]
    out.append(f'<text x="{BLOCK_W / 2:.1f}" y="58" class="m-title" text-anchor="middle">{esc(title)}</text>')
    if lang == "zh":
        out.append(f'<text x="{BLOCK_W - 26:.1f}" y="56" class="m-sub" text-anchor="end">{month}</text>')
    wk_names = ZH_WEEK if lang == "zh" else EN_WEEK
    for i, name in enumerate(wk_names):
        cls = "wk wk-off" if i in (0, 6) else "wk"
        out.append(_t(esc, (i + 0.5) * CELL_W, HEAD_H + 28, name, cls))
    out.append(f'<line class="m-rule" x1="14" y1="{HEAD_H + WEEKDAY_H:.1f}" x2="{BLOCK_W - 14:.1f}" y2="{HEAD_H + WEEKDAY_H:.1f}"/>')

    first = date(year, month, 1)
    start_col = (first.weekday() + 1) % 7  # 週日 = 0
    d = first
    while d.month == month:
        idx = start_col + d.day - 1
        r, c = divmod(idx, 7)
        x = c * CELL_W
        y = HEAD_H + WEEKDAY_H + r * ROW_H
        day = days_by_date.get(d.strftime("%Y%m%d"))
        kind = classify(day, c) if day else ("weekend" if c in (0, 6) else "weekday")
        cx = x + CELL_W / 2
        out.append(f'<g class="d d-{kind}">')
        if kind != "weekday":
            out.append(f'<rect class="bg" x="{x + 2:.1f}" y="{y + 2:.1f}" width="{CELL_W - 4:.1f}" height="{ROW_H - 4:.1f}" rx="10"/>')
        out.append(_t(esc, cx, y + 32, str(d.day), "num"))

        label_cls, lines = None, []
        if day and kind == "holiday":
            label_cls, lines = "lab lab-hol", holiday_label(day["description"], lang).split("|")
        elif kind == "makeup":
            label_cls, lines = "lab lab-work", ["補班" if lang == "zh" else "Workday"]
        elif lang == "zh" and day:
            term = (day.get("lunar") or {}).get("solarTerm")
            if term:
                label_cls, lines = "lab lab-term", [term]
            else:
                lab = lunar_label(day.get("lunar"))
                if lab:
                    label_cls, lines = "lab lab-lunar", [lab]
        for i, line in enumerate(lines):
            cls = label_cls + (" long" if (lang == "zh" and len(line) > 4) or (lang != "zh" and len(line) > 11) else "")
            out.append(_t(esc, cx, y + 56 + i * 18, line, cls))
        out.append("</g>")
        d = date.fromordinal(d.toordinal() + 1)
    out.append("</g>")
    return "\n".join(out)


STYLE = f"""
.bg-page{{fill:#FFFFFF}}
.m-card{{fill:#FBFBFD;stroke:#E4E6EE;stroke-width:2}}
.m-title{{font:800 46px {{font}};fill:#1E2A4A}}
.m-sub{{font:700 30px {{font_en}};fill:#B9BED0}}
.m-rule{{stroke:#E4E6EE;stroke-width:2}}
.wk{{font:700 21px {{font}};fill:#64708C}}
.wk-off{{fill:#7A56C4}}
.num{{font:700 32px {{font_en}};fill:#1E2A4A}}
.d-weekend .bg{{fill:#EFE9FB}}
.d-weekend .num{{fill:#6B45B8}}
.d-holiday .bg{{fill:#FFD9E1}}
.d-holiday .num{{fill:#B3203F}}
.d-makeup .bg{{fill:#E3EEFF;stroke:#2F6FEB;stroke-width:3}}
.d-makeup .num{{fill:#1D56C9}}
.lab{{font:600 17px {{font}}}}
.lab-lunar{{fill:#8B93A9}}
.lab-term{{fill:#0F766E;font-weight:700}}
.lab-hol{{fill:#B3203F;font-weight:800;font-size:19px}}
.lab-hol.long{{font-size:16px}}
.lab-work{{fill:#1D56C9;font-weight:800;font-size:19px}}
.title{{font:800 104px {{font}};fill:#1E2A4A}}
.title-accent{{fill:#C2264B}}
.sub{{font:600 34px {{font}};fill:#64708C}}
.leg{{font:600 26px {{font}};fill:#475068}}
.foot{{font:500 22px {{font}};fill:#8B93A9}}
""".replace("{{font}}", "{font}").replace("{{font_en}}", "{font_en}")


def render_poster_svg(esc, year, calendar, lang):
    """回傳完整 <svg>。calendar 為 data/<year>.json 的內容。"""
    days_by_date = {e["date"]: e for e in calendar}
    font = FONT_ZH if lang == "zh" else FONT_EN
    css = STYLE.replace("{font}", font).replace("{font_en}", FONT_EN)
    if lang == "zh":
        title = f"{year} 年行事曆"
        accent = f"（民國 {roc_year(year)} 年）"
        subtitle = "政府行政機關辦公日曆表・含農曆、節氣與補班日"
        label_title = f"{year} 年台灣行事曆（民國 {roc_year(year)} 年）"
        legend = [("weekend", "週六、週日"), ("holiday", "國定假日・補假"), ("makeup", "補班日")]
        foot = "資料：行政院人事行政總處（政府資料開放平台 14718），以政府最終公告為準　|　tw-holidays.gooliya.com"
    else:
        title = f"Taiwan Calendar {year}"
        accent = f"  ROC {roc_year(year)}"
        subtitle = "Public holidays & make-up workdays"
        label_title = f"{year} Taiwan public holidays calendar (ROC year {roc_year(year)})"
        legend = [("weekend", "Weekend"), ("holiday", "Public holiday / day off"), ("makeup", "Make-up workday")]
        foot = "Source: DGPA, Executive Yuan (data.gov.tw dataset 14718). Official announcements prevail.  |  tw-holidays.gooliya.com"

    desc_text = ("12 個月全年行事曆，標示週末、國定假日、補假與補班日。" if lang == "zh"
                 else "Full-year, 12-month calendar marking weekends, public holidays, days off and make-up workdays in Taiwan.")
    parts = [
        f'<svg id="poster" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-labelledby="poster-t poster-d">',
        f'<title id="poster-t">{esc(label_title)}</title>',
        f'<desc id="poster-d">{esc(desc_text)}</desc>',
        f'<style>{css}</style>',
        f'<rect class="bg-page" width="{W}" height="{H}"/>',
        f'<rect x="{MARGIN}" y="92" width="14" height="150" rx="7" fill="#C2264B"/>',
        f'<text x="{MARGIN + 44}" y="182" class="title">{esc(title)}<tspan class="title-accent">{esc(accent)}</tspan></text>',
        f'<text x="{MARGIN + 44}" y="248" class="sub">{esc(subtitle)}</text>',
    ]
    # 圖例（右上）
    lx = W - MARGIN
    for kind, text in reversed(legend):
        width = 56 + len(text) * (26 if lang == "zh" else 13.5) + 28
        lx -= width
        fill = {"weekend": "#EFE9FB", "holiday": "#FFD9E1", "makeup": "#E3EEFF"}[kind]
        stroke = ' stroke="#2F6FEB" stroke-width="3"' if kind == "makeup" else ""
        parts.append(f'<rect x="{lx:.1f}" y="204" width="40" height="40" rx="10" fill="{fill}"{stroke}/>')
        parts.append(f'<text x="{lx + 54:.1f}" y="235" class="leg">{esc(text)}</text>')
    for m in range(1, 13):
        parts.append(render_month(esc, year, m, days_by_date, lang))
    parts.append(f'<text x="{W / 2}" y="{H - 70}" class="foot" text-anchor="middle">{esc(foot)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 頁面
# ---------------------------------------------------------------------------

PAGE_CSS = """<style>
.poster-tools{display:flex;flex-wrap:wrap;gap:.6rem;margin:1rem 0}
.poster-btn{display:inline-flex;align-items:center;gap:.4rem;min-height:44px;padding:.5rem 1.1rem;border-radius:999px;
 border:1px solid var(--border);background:var(--surface);color:var(--text);font:inherit;font-weight:700;cursor:pointer;text-decoration:none}
.poster-btn:hover{background:var(--surface-2)}
.poster-btn.primary{background:var(--primary);border-color:var(--primary);color:#fff}
@media (prefers-color-scheme:dark){.poster-btn.primary{color:#0F172A}}
.poster-fig{margin:1rem 0;overflow-x:auto;border-radius:var(--radius);border:1px solid var(--border);background:#fff;box-shadow:var(--shadow)}
.poster-fig svg{display:block;width:100%;min-width:720px;height:auto}
.nav-label{color:var(--muted);font-size:.85rem;align-self:center}
.poster-hint{color:var(--muted);font-size:.9rem;margin:.25rem 0 1rem}
.poster-list{columns:2 16rem;padding-left:1.2rem}
@page{size:A4 portrait;margin:6mm}
@media print{
 .skip-link,.site-header,.breadcrumb,.poster-tools,.poster-hint,.poster-after,.site-footer,h1,.lead{display:none!important}
 body{background:#fff}.container{max-width:none;padding:0}
 .poster-fig{border:0;box-shadow:none;border-radius:0;overflow:visible}
 .poster-fig svg{min-width:0;width:100%;height:auto}
}
</style>"""

DOWNLOAD_JS = """<script>
(function () {
  var svg = document.getElementById('poster');
  var btn = document.getElementById('dl-png');
  if (!svg || !btn) return;
  var label = btn.textContent;
  btn.addEventListener('click', function () {
    var W = 2480, H = 3508; // A4 @ 300dpi
    var xml = new XMLSerializer().serializeToString(svg);
    var img = new Image();
    btn.disabled = true;
    img.onload = function () {
      var c = document.createElement('canvas');
      c.width = W; c.height = H;
      var ctx = c.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, W, H);
      ctx.drawImage(img, 0, 0, W, H);
      c.toBlob(function (blob) {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = btn.getAttribute('data-filename');
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
        btn.disabled = false;
      }, 'image/png');
    };
    img.onerror = function () { btn.disabled = false; };
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(xml);
  });
  var pr = document.getElementById('print-pdf');
  if (pr) pr.addEventListener('click', function () { window.print(); });
})();
</script>"""


def faq_block(esc, faqs, zh):
    parts = [f'<section class="card faq poster-after" aria-labelledby="faq-h"><h2 id="faq-h">{"常見問題" if zh else "FAQ"}</h2>']
    for q, a in faqs:
        parts.append(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>")
    parts.append("</section>")
    return "\n".join(parts)


def render_poster_page(gp, year, calendar, holidays, years, lang):
    """gp：generate_pages 模組（提供 SITE、page_head 等）。"""
    esc = gp.esc
    zh = lang == "zh"
    canonical = f"{gp.SITE}{poster_path(year, lang)}"
    zh_url = f"{gp.SITE}{poster_path(year, 'zh')}"
    en_url = f"{gp.SITE}{poster_path(year, 'en')}"
    hub_url = f"{gp.SITE}/{year}/"

    holiday_names = []
    seen = set()
    for h in holidays:
        key = (h["date"], h["description"])
        if key not in seen:
            seen.add(key)
            holiday_names.append(h)

    if zh:
        title = f"{year} 年行事曆（民國 {roc_year(year)} 年）A4 一頁圖・可下載 PNG／PDF｜{gp.SITE_NAME}"
        description = (f"{year} 年（民國 {roc_year(year)} 年）台灣行事曆一頁圖：12 個月一張 A4，標示週末、國定假日、補假、補班日，"
                       f"含農曆與節氣。免費下載高解析 PNG 或列印成 PDF。")
        h1 = f"{year} 年行事曆（民國 {roc_year(year)} 年）"
        lead = (f"把 {year} 年全年 12 個月放在一張 A4 直式圖上：週末與國定假日上色、補班日加藍框，並標示農曆與節氣。"
                f"可以直接預覽，也能下載 PNG 或存成 PDF 列印。資料與政府辦公日曆表同步。")
        btn_png, btn_pdf, hint = "下載 PNG（A4 300dpi）", "列印／存成 PDF", "手機上看不清楚？按「下載 PNG」存成圖片再放大。"
        other_label = "English version"
        list_h = f"{year} 年國定假日一覽"
        back = f"{year} 年連假與請假攻略"
        dl_name = f"taiwan-holidays-{year}-zh.png"
        crumbs = [("首頁", f"{gp.SITE}/"), (f"{year} 年國定假日", hub_url), ("年曆一頁圖", canonical)]
        items = "".join(
            f'<li>{gp.time_tag(gp.parse_compact(h["date"]), gp.mdw(gp.parse_compact(h["date"])))}　{esc(h["description"])}</li>'
            for h in holiday_names)
        api_note = (f'資料來自政府資料開放平台，可用 <a href="/api.html">JSON API</a> 取得；'
                    f'<a href="{gp.SITE}/calendar/">訂閱行事曆（.ics）</a>可自動同步到手機日曆。')
    else:
        title = f"Taiwan Public Holidays {year} Calendar – A4 One-Page, PNG & PDF Download｜{gp.SITE_NAME}"
        description = (f"Taiwan {year} calendar on a single A4 page: all 12 months with public holidays, days off and make-up "
                       f"workdays marked. Free high-resolution PNG download or print to PDF.")
        h1 = f"Taiwan Public Holidays Calendar {year}"
        lead = (f"All 12 months of {year} on one A4 portrait page. Weekends and Taiwan's public holidays are shaded, and "
                f"make-up workdays (when a weekend day becomes a working day) are outlined in blue. Preview it here, "
                f"download a PNG, or save it as a PDF.")
        btn_png, btn_pdf, hint = "Download PNG (A4, 300 dpi)", "Print / Save as PDF", "Hard to read on a phone? Download the PNG and zoom in."
        other_label = "中文版"
        list_h = f"Taiwan public holidays in {year}"
        back = f"{year} holidays and long weekends (中文)"
        dl_name = f"taiwan-holidays-{year}-en.png"
        crumbs = [("Home", f"{gp.SITE}/"), (f"{year} Calendar", canonical)]
        items = "".join(
            f'<li>{gp.time_tag(gp.parse_compact(h["date"]), en_date(gp.parse_compact(h["date"])))}'
            f'　{esc(EN_FULL.get(h["description"], h["description"]))}</li>' for h in holiday_names)
        api_note = (f'Data comes from the Taiwan government open-data portal. Use the free <a href="/api.html">JSON API</a> '
                    f'(English files: <code>holidays-en.json</code>, <code>calendar-en.json</code>), or '
                    f'<a href="{gp.SITE}/calendar/">subscribe to the .ics calendar</a>.')

    n_holidays = len({h["description"] for h in holidays if h["description"] not in ("補假",)})
    makeup_days = [e for e in calendar if (not e["isHoliday"]) and any(k in e["description"] for k in MAKEUP_KEYWORDS)]
    if zh:
        faqs = [
            (f"{year} 年行事曆一頁圖可以免費下載或列印嗎？",
             f"可以。本頁提供 A4 直式、300dpi 的 PNG 下載，也能按「列印／存成 PDF」輸出 PDF；資料以 CC BY 4.0 釋出，個人與公司內部使用都沒問題。"),
            (f"{year} 年有哪些補班日？",
             f"{year} 年共有 {len(makeup_days)} 天補班日，年曆中以藍框標示。" if makeup_days
             else f"{year} 年沒有補班日，所有平日放假都不需要在週末補上班。"),
            (f"圖上的假日資料從哪裡來？",
             "來源是行政院人事行政總處公告、政府資料開放平台的「中華民國政府行政機關辦公日曆表」，每月自動同步；實際放假以政府最終公告為準。"),
        ]
    else:
        faqs = [
            (f"Can I download or print the Taiwan {year} calendar for free?",
             "Yes. Download the A4 portrait PNG (300 dpi) or press 'Print / Save as PDF' to export a PDF. The data is released under CC BY 4.0."),
            (f"Are there make-up workdays in Taiwan in {year}?",
             f"Yes, {len(makeup_days)} make-up workday(s) in {year}; they are outlined in blue on the calendar." if makeup_days
             else f"No. Taiwan has no make-up workdays in {year}, so no weekend day is converted into a working day."),
            ("Where does the holiday data come from?",
             "It comes from the Government Office Calendar published by the DGPA, Executive Yuan, via data.gov.tw (dataset 14718), synced monthly. Official announcements always prevail."),
        ]
    webpage = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": h1,
        "description": description,
        "url": canonical,
        "inLanguage": "zh-TW" if zh else "en",
        "isPartOf": {"@type": "WebSite", "name": gp.SITE_NAME, "url": f"{gp.SITE}/"},
        "about": {"@type": "Place", "name": "Taiwan"},
        "primaryImageOfPage": {"@type": "ImageObject", "name": h1, "encodingFormat": "image/svg+xml"},
    }
    ld = "\n".join([gp.json_ld(webpage), gp.json_ld(gp.breadcrumb_ld(crumbs)), gp.json_ld(gp.faq_ld(faqs))])
    alt = (f'    <link rel="alternate" hreflang="zh-TW" href="{zh_url}">\n'
           f'    <link rel="alternate" hreflang="en" href="{en_url}">\n'
           f'    <link rel="alternate" hreflang="x-default" href="{zh_url}">\n')
    head = gp.page_head(title, description, canonical, "article", ld, extra_head=alt + PAGE_CSS + "\n",
                        lang="zh-TW" if zh else "en", locale="zh_TW" if zh else "en_US")

    def nav_link(href, text, current=False, hl=None):
        cur = ' aria-current="page"' if current else ""
        lang_attr = f' hreflang="{hl}"' if hl else ""
        return f'<a href="{href}"{lang_attr}{cur}>{esc(text)}</a>'

    year_links = "".join(
        nav_link(poster_path(y, lang), f"{y} 年曆" if zh else f"{y}", current=(y == year)) for y in years)
    switch = (nav_link(poster_path(year, "en"), "EN", hl="en") if zh else nav_link(poster_path(year, "zh"), "中文", hl="zh-TW"))
    if zh:
        chrome_top = f"""<body>
    <a class="skip-link" href="#main">跳到主要內容</a>
    <header class="site-header">
        <div class="container">
            <a class="brand" href="/">{gp.SITE_NAME}<span>台灣國定假日行事曆</span></a>
            <nav class="site-nav" aria-label="網站導覽">{nav_link("/", "互動行事曆")}{nav_link(f"/{year}/", f"{year} 連假")}{year_links}{switch}{nav_link("/api.html", "JSON API")}</nav>
        </div>
    </header>
    <main id="main" class="container">
"""
        chrome_bottom = gp.site_footer()
    else:
        chrome_top = f"""<body>
    <a class="skip-link" href="#main">Skip to main content</a>
    <header class="site-header">
        <div class="container">
            <a class="brand" href="/">{gp.SITE_NAME}<span>Taiwan public holidays</span></a>
            <nav class="site-nav" aria-label="Site">{nav_link("/en/", "Home")}{nav_link(f"/en/{year}/", f"Holidays {year}")}<span class="nav-label">Calendar:</span>{year_links}{switch}{nav_link("/", "Interactive calendar")}{nav_link("/api.html", "JSON API")}</nav>
        </div>
    </header>
    <main id="main" class="container">
"""
        chrome_bottom = f"""    </main>
    <footer class="site-footer container">
        <p>Source: <a href="{gp.DATA_SOURCE_URL}" rel="noopener noreferrer">Taiwan government open data portal, DGPA Executive Yuan "Government Office Calendar"</a> (dataset 14718), synced monthly. Official announcements prevail.</p>
        <p>Data under <a href="{gp.LICENSE_URL}" rel="noopener noreferrer">CC BY 4.0</a>, code under MIT. Source: <a href="{gp.GITHUB}" rel="noopener noreferrer">GitHub imsyuan/taiwan-holidays</a>. Generated from <code>data/</code> by <code>scripts/generate_pages.py</code>.</p>
    </footer>
</body>
</html>
"""

    body = f"""    {gp.breadcrumb_html(crumbs)}
    <h1>{esc(h1)}</h1>
    <p class="lead">{esc(lead)}</p>
    <div class="poster-tools">
        <button type="button" id="dl-png" class="poster-btn primary" data-filename="{dl_name}">{esc(btn_png)}</button>
        <button type="button" id="print-pdf" class="poster-btn">{esc(btn_pdf)}</button>
        <a class="poster-btn" href="{poster_path(year, 'en' if zh else 'zh')}" hreflang="{'en' if zh else 'zh-TW'}">{other_label}</a>
    </div>
    <p class="poster-hint">{esc(hint)}</p>
    <figure class="poster-fig">
{render_poster_svg(esc, year, calendar, lang)}
    </figure>
    <section class="poster-after card" aria-labelledby="hol-h">
        <h2 id="hol-h">{esc(list_h)}</h2>
        <ul class="poster-list">{items}</ul>
        <p class="note">{api_note}</p>
        <p><a href="/{year}/">{esc(back)}</a></p>
    </section>
    {faq_block(esc, faqs, zh)}
"""
    return head + chrome_top + body + chrome_bottom.replace("</body>", DOWNLOAD_JS + "\n</body>")
