#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英文靜態頁面：/en/、/en/<year>/、/en/<year>/<slug>/。

與中文頁共用 generate_pages.py 算出的連假（runs）與請假方案（plans），數字完全一致，
只把版面與文字換成英文，讓不讀中文的人（旅客、外商、遠端工作者、英文 AI 答題引擎）
能用英文關鍵字搜尋到、並直接引用。

為避免循環匯入，generate_pages 模組以 gp 參數傳入（與 poster.py 相同做法）。
"""

import re
from datetime import timedelta

import poster

EN_MONTHS = poster.EN_MONTHS
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEK3 = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# slug 前綴 → (英文名稱, 種類)。種類決定名稱結尾：春節放 holiday，其餘 long weekend。
RUN_EN = {
    "lunar-new-year": ("Lunar New Year", "holiday"),
    "tomb-sweeping": ("Tomb Sweeping Day (Qingming)", "long weekend"),
    "dragon-boat": ("Dragon Boat Festival", "long weekend"),
    "mid-autumn": ("Mid-Autumn Festival", "long weekend"),
    "national-day": ("National Day (Double Ten)", "long weekend"),
    "new-year": ("New Year's Day", "long weekend"),
    "peace-memorial-day": ("Peace Memorial Day (228)", "long weekend"),
    "labor-day": ("Labor Day", "long weekend"),
    "teachers-day": ("Confucius Birthday (Teachers' Day)", "long weekend"),
    "taiwan-retrocession-day": ("Taiwan Retrocession Day", "long weekend"),
    "constitution-day": ("Constitution Day", "long weekend"),
}


# ---------------------------------------------------------------------------
# 格式化
# ---------------------------------------------------------------------------

def mon_day(d):
    return f"{EN_MONTHS[d.month - 1][:3]} {d.day}"


def mdw(d):
    return f"{mon_day(d)} ({WEEK3[d.weekday()]})"


def long_date(d):
    return f"{WEEKDAYS[d.weekday()]}, {EN_MONTHS[d.month - 1]} {d.day}, {d.year}"


def span(s, e):
    return f"{mon_day(s)}–{mon_day(e)}"


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def holiday_en(desc):
    return poster.EN_FULL.get(desc, desc)


def run_en(run):
    """回傳 (名稱, 短標籤)。slug 末尾的 -2、-3 不影響對應。"""
    base = re.sub(r"-\d+$", "", run["slug"])
    if base in RUN_EN:
        label, kind = RUN_EN[base]
        suffix = re.search(r"-(\d+)$", run["slug"])
        name = f"{label} {kind}" + (f" ({suffix.group(1)})" if suffix else "")
        return name, label
    s = run["start"]
    return f"Long weekend from {mon_day(s)}", f"{mon_day(s)} long weekend"


def run_names_en(run):
    out = []
    for d in run["holiday_names"]:
        n = holiday_en(d)
        if n not in out:
            out.append(n)
    return out


def plan_sentence(gp, plan):
    leave = [gp.iso_to_date(x) for x in plan["leaveDates"]]
    s, e = gp.iso_to_date(plan["offRange"]["start"]), gp.iso_to_date(plan["offRange"]["end"])
    return (f"take {plural(plan['leaveSpent'], 'day')} off ({', '.join(mdw(d) for d in leave)}) "
            f"for {plan['totalDaysOff']} days in a row, {mdw(s)} to {mdw(e)}")


def en_path(year=None, slug=None):
    if year is None:
        return "/en/"
    return f"/en/{year}/" if slug is None else f"/en/{year}/{slug}/"


def zh_counterpart(year=None, slug=None):
    if year is None:
        return "/"
    return f"/{year}/" if slug is None else f"/{year}/{slug}/"


# ---------------------------------------------------------------------------
# 外框
# ---------------------------------------------------------------------------

def alternates(gp, year=None, slug=None):
    zh = f"{gp.SITE}{zh_counterpart(year, slug)}"
    en = f"{gp.SITE}{en_path(year, slug)}"
    return (f'    <link rel="alternate" hreflang="zh-TW" href="{zh}">\n'
            f'    <link rel="alternate" hreflang="en" href="{en}">\n'
            f'    <link rel="alternate" hreflang="x-default" href="{zh if year is None else en}">\n')


def head(gp, title, description, canonical, og_type, ld, year=None, slug=None, extra=""):
    return gp.page_head(title, description, canonical, og_type, ld,
                        extra_head=alternates(gp, year, slug) + extra, lang="en", locale="en_US")


def header(gp, years, year=None, slug=None):
    def a(href, text, cur=False, hl=None):
        return (f'<a href="{href}"' + (f' hreflang="{hl}"' if hl else "") +
                (' aria-current="page"' if cur else "") + f">{gp.esc(text)}</a>")
    links = [a("/en/", "Home", cur=(year is None))]
    links += [a(en_path(y), str(y), cur=(y == year and slug is None)) for y in years]
    links.append(a(zh_counterpart(year, slug), "中文", hl="zh-TW"))
    links.append(a("/", "Interactive calendar"))
    links.append(a("/api.html", "JSON API"))
    return f"""<body>
    <a class="skip-link" href="#main">Skip to main content</a>
    <header class="site-header">
        <div class="container">
            <a class="brand" href="/en/">{gp.SITE_NAME}<span>Taiwan public holidays</span></a>
            <nav class="site-nav" aria-label="Site">{''.join(links)}</nav>
        </div>
    </header>
    <main id="main" class="container">
"""


def footer(gp):
    return f"""    </main>
    <footer class="site-footer container">
        <p>Source: <a href="{gp.DATA_SOURCE_URL}" rel="noopener noreferrer">Taiwan government open data portal, DGPA Executive Yuan "Government Office Calendar"</a> (dataset 14718), synced monthly. Official government announcements always prevail.</p>
        <p>Data under <a href="{gp.LICENSE_URL}" rel="noopener noreferrer">CC BY 4.0</a>, code under MIT. Source code: <a href="{gp.GITHUB}" rel="noopener noreferrer">GitHub imsyuan/taiwan-holidays</a>. This page is generated from <code>data/</code> by <code>scripts/generate_pages.py</code>; it contains no hand-maintained numbers.</p>
    </footer>
</body>
</html>
"""


def crumbs_html(gp, items):
    lis = []
    for i, (name, href) in enumerate(items):
        if i == len(items) - 1 or not href:
            lis.append(f'<li aria-current="page">{gp.esc(name)}</li>')
        else:
            lis.append(f'<li><a href="{gp.esc(href)}">{gp.esc(name)}</a></li>')
    return f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol>{"".join(lis)}</ol></nav>'


def faq_html(gp, faqs):
    parts = ['<section class="card faq" aria-labelledby="faq-h"><h2 id="faq-h">FAQ</h2>']
    for q, a in faqs:
        parts.append(f"<h3>{gp.esc(q)}</h3><p>{gp.esc(a)}</p>")
    parts.append("</section>")
    return "\n".join(parts)


def tt(gp, d, text=None):
    return gp.time_tag(d, text if text is not None else mdw(d))


# ---------------------------------------------------------------------------
# 文字內容
# ---------------------------------------------------------------------------

def makeup_sentence(gp, ym, since):
    y = ym["year"]
    if ym["makeup"]:
        return (f"Taiwan has {plural(len(ym['makeup']), 'make-up workday')} in {y}: "
                f"{', '.join(mdw(d) for d in ym['makeup_dates'])}. A make-up workday is a normal working day "
                f"(usually a Saturday) that replaces a weekday off, so it counts as a workday for leave planning.")
    text = f"Taiwan has no make-up workdays in {y}."
    if since is not None and since <= y:
        text += (" Since " + (f"{since}" if since < y else f"{y}") +
                 ", the official government calendar no longer includes make-up workdays; when a public holiday "
                 "falls on a Saturday or Sunday, the government gives a compensatory day off on a nearby weekday instead.")
    return text


def hub_faqs(gp, ym, since):
    y = ym["year"]
    runs = ym["runs"]
    faqs = [(
        f"How many public holidays does Taiwan have in {y}?",
        f"The official calendar lists {len(ym['holidays'])} holiday entries for {y}, including {ym['buja_count']} "
        f"compensatory days off and {ym['weekend_holiday_count']} holidays that fall on a Saturday or Sunday. "
        f"Of the year's {ym['total_days']} days, {ym['off_days']} are non-working days (weekends included) and "
        f"{ym['work_days']} are working days.",
    )]
    lny = next((r for r in runs if r["slug"].startswith("lunar-new-year")), None)
    if lny:
        faqs.append((
            f"When is the Lunar New Year holiday in Taiwan in {y}?",
            f"The {y} Lunar New Year holiday runs from {long_date(lny['start'])} to {long_date(lny['end'])}, "
            f"{lny['length']} days in a row, covering {', '.join(run_names_en(lny))}"
            + (f" and {lny['weekend_days']} weekend days." if lny["weekend_days"] else "."),
        ))
    if ym["longest"]:
        lg = ym["longest"]
        name, _ = run_en(lg)
        a = (f"The longest stretch in {y} is the {name}: {long_date(lg['start'])} to {long_date(lg['end'])}, "
             f"{lg['length']} days.")
        if lg.get("combo"):
            a += (f" Taking {plural(lg['combo']['leaveSpent'], 'day')} of leave around it extends the break to "
                  f"{lg['combo']['totalDaysOff']} days.")
        faqs.append((f"What is the longest holiday break in Taiwan in {y}?", a))
    faqs.append((f"Does Taiwan have make-up workdays in {y}?", makeup_sentence(gp, ym, since)))
    if ym["plans"]:
        best = ym["plans"][0]
        a = f"The most efficient plan for {y}: {plan_sentence(gp, best)}."
        if len(ym["plans"]) > 1:
            a += f" Runner-up: {plan_sentence(gp, ym['plans'][1])}."
        faqs.append((f"Which days should I take off in {y} to get the longest break?", a))
    if runs:
        faqs.append((
            f"How many long weekends (3+ days) does Taiwan have in {y}?",
            f"{len(runs)} long weekends of 3 or more consecutive days off (weekends included): "
            + "; ".join(f"{run_en(r)[0]} {span(r['start'], r['end'])} ({r['length']} days)" for r in runs) + ".",
        ))
    faqs.append((
        f"Where does the {y} Taiwan holiday data come from, and can I use it in code?",
        f"It comes from the Government Office Calendar published by the DGPA, Executive Yuan, on data.gov.tw "
        f"(dataset 14718), synced monthly. English JSON: {gp.CDN}/{y}/holidays-en.json (public holidays) and "
        f"{gp.CDN}/{y}/calendar-en.json (full-year calendar). AI agents can use the MCP server {gp.MCP_ENDPOINT} "
        f"to count workdays and plan leave.",
    ))
    return faqs[:8]


def run_faqs(gp, ym, run, idx):
    y = ym["year"]
    runs = ym["runs"]
    name, _ = run_en(run)
    names = ", ".join(run_names_en(run))
    faqs = [(
        f"When is the {name} in Taiwan in {y}?",
        f"The {y} {name} runs from {long_date(run['start'])} to {long_date(run['end'])}, {run['length']} days in a row: "
        f"{run['weekend_days']} weekend days and {run['length'] - run['weekend_days']} weekday holidays ({names}).",
    )]
    all_plans = list(run["plans"]) + ([run["combo"]] if run.get("combo") else [])
    if all_plans:
        best_eff = all_plans[0]
        best_long = max(all_plans, key=lambda p: (p["totalDaysOff"], -p["leaveSpent"]))
        a = f"Most efficient: {plan_sentence(gp, best_eff)}."
        if best_long is not best_eff:
            a += f" Longest break: {plan_sentence(gp, best_long)}."
        faqs.append((f"How many days of leave do I need to extend the {name} {y}?", a))
    near = [d for d in ym["makeup_dates"] if run["start"] - timedelta(days=14) <= d <= run["end"] + timedelta(days=14)]
    if near:
        a = f"Yes. There are make-up workdays within two weeks of the {name}: {', '.join(mdw(d) for d in near)}."
    elif not ym["makeup"]:
        a = f"No. Taiwan has no make-up workdays in {y}, so the weeks around the {name} follow the normal Monday-to-Friday schedule."
    else:
        a = (f"No make-up workdays fall within two weeks of the {name}. "
             f"The {y} make-up workdays are {', '.join(mdw(d) for d in ym['makeup_dates'])}.")
    faqs.append((f"Do I have to work a make-up day around the {name} {y}?", a))
    if run["buja_days"]:
        days = [gp.parse_compact(e["date"]) for e in run["entries"] if e["description"] == "補假"]
        faqs.append((
            f"Why does the {name} {y} include a compensatory day off?",
            f"{plural(run['buja_days'], 'day')} in this break {'is' if run['buja_days'] == 1 else 'are'} compensatory leave "
            f"({', '.join(mdw(d) for d in days)}). When a public holiday falls on a Saturday or Sunday, the government "
            f"gives an extra day off on a nearby weekday, and it is an official day off.",
        ))
    prev_run = runs[idx - 1] if idx > 0 else None
    next_run = runs[idx + 1] if idx + 1 < len(runs) else None
    if next_run:
        gap = (next_run["start"] - run["end"]).days - 1
        nn, _ = run_en(next_run)
        a = (f"After the {name}, the next long weekend in {y} is the {nn} ({long_date(next_run['start'])} to "
             f"{long_date(next_run['end'])}, {next_run['length']} days), {gap} days later.")
    else:
        a = f"The {name} is the last long weekend of 3 or more days in {y}."
        if prev_run:
            pn, _ = run_en(prev_run)
            a += f" The previous one is the {pn} ({span(prev_run['start'], prev_run['end'])}, {prev_run['length']} days)."
    faqs.append((f"What is the next long weekend in Taiwan after the {name} {y}?", a))
    return faqs


def plan_html(gp, index, plan, run_name):
    leave = [gp.iso_to_date(x) for x in plan["leaveDates"]]
    s, e = gp.iso_to_date(plan["offRange"]["start"]), gp.iso_to_date(plan["offRange"]["end"])
    combo = plan.get("combined")
    title = f"Plan {index + 1}" + (" (Plans 1 + 2 combined: leave before and after)" if combo else "")
    eff = f"{round(plan['efficiency'], 2):g}"
    return f"""<article class="plan{' combo' if combo else ''}">
<h3>{gp.esc(title)}</h3>
<p class="plan-summary">Take <b>{plan['leaveSpent']}</b> {'day' if plan['leaveSpent'] == 1 else 'days'} off, get <b>{plan['totalDaysOff']}</b> days in a row ({eff} days of break per day of leave)</p>
<p>Leave days: {', '.join(tt(gp, d) for d in leave)}</p>
<p>Break: {tt(gp, s)} to {tt(gp, e)}, {plan['totalDaysOff']} days in total: {len(leave)} leave {'day' if len(leave) == 1 else 'days'}, the other {plan['totalDaysOff'] - len(leave)} are the {gp.esc(run_name)}, weekends or other days off.</p>
</article>"""


def day_table(gp, ym, run, plan, all_by_date):
    s, e = run["start"], run["end"]
    leave = set()
    if plan:
        s = min(s, gp.iso_to_date(plan["offRange"]["start"]))
        e = max(e, gp.iso_to_date(plan["offRange"]["end"]))
        leave = {gp.iso_to_date(x) for x in plan["leaveDates"]}
    start, end = gp.monday_of(s), gp.sunday_of(e)
    rows = []
    d = start
    while d <= end:
        en = all_by_date.get(d)
        if en is not None:
            if d in leave:
                status, cls, note, badge = "Leave", "is-leave", "Plan 1", "badge-leave"
            elif en["isHoliday"]:
                status, cls, badge = "Day off", "is-off", "badge-off"
                note = holiday_en(en["description"]) if en["description"] else "Weekend"
            else:
                status, cls, badge = "Work", "", "badge-work"
                note = holiday_en(en["description"]) if en["description"] else ""
            rows.append(f'<tr class="{cls}"><th scope="row">{gp.time_tag(d, d.isoformat())}</th><td>{WEEK3[d.weekday()]}</td>'
                        f'<td><span class="badge {badge}">{status}</span></td><td class="wrap">{gp.esc(note)}</td></tr>')
        d += timedelta(days=1)
    return start, end, "\n".join(rows)


# ---------------------------------------------------------------------------
# 頁面
# ---------------------------------------------------------------------------

def render_hub(gp, ym, years, since):
    y = ym["year"]
    runs = ym["runs"]
    lg = ym["longest"]
    canonical = f"{gp.SITE}{en_path(y)}"
    title = f"Taiwan Public Holidays {y} – Long Weekends, Make-up Workdays & Leave Planner｜{gp.SITE_NAME}"
    lg_text = f", the longest being the {run_en(lg)[0]} ({span(lg['start'], lg['end'])}, {lg['length']} days)" if lg else ""
    description = (f"Taiwan public holidays {y}: {len(ym['holidays'])} official holiday entries, {len(runs)} long weekends{lg_text}. "
                   f"{'No make-up workdays' if not ym['makeup'] else plural(len(ym['makeup']), 'make-up workday')} in {y}. "
                   f"Holiday table, leave-planning tips, FAQ and free JSON API.")
    prev_year = y - 1 if (y - 1) in years else None
    next_year = y + 1 if (y + 1) in years else None
    crumbs = [("Home", f"{gp.SITE}/en/"), (f"{y} holidays", canonical)]
    faqs = hub_faqs(gp, ym, since)
    dataset = {
        "@context": "https://schema.org", "@type": "Dataset",
        "name": f"Taiwan public holidays and make-up workdays {y}",
        "description": f"Official Taiwan government office calendar for {y}: {len(ym['holidays'])} public holiday entries, "
                       f"{len(ym['makeup'])} make-up workdays, and a daily isHoliday flag, in JSON (English and Chinese).",
        "url": canonical, "inLanguage": "en",
        "keywords": [f"Taiwan public holidays {y}", f"Taiwan holidays {y}", f"Taiwan make-up workdays {y}", "Taiwan holiday API"],
        "license": gp.LICENSE_URL,
        "temporalCoverage": f"{y}-01-01/{y}-12-31",
        "spatialCoverage": {"@type": "Place", "name": "Taiwan"},
        "creator": {"@type": "Organization", "name": "Gooliya", "url": "https://www.gooliya.com/"},
        "isBasedOn": {"@type": "CreativeWork", "name": "Government Office Calendar (DGPA, Executive Yuan)", "url": gp.DATA_SOURCE_URL},
        "distribution": [
            {"@type": "DataDownload", "name": f"{y} public holidays (English)", "encodingFormat": "application/json", "contentUrl": f"{gp.CDN}/{y}/holidays-en.json"},
            {"@type": "DataDownload", "name": f"{y} full-year calendar (English)", "encodingFormat": "application/json", "contentUrl": f"{gp.CDN}/{y}/calendar-en.json"},
        ],
    }
    ld = "\n".join([gp.json_ld(gp.breadcrumb_ld(crumbs)), gp.json_ld(gp.faq_ld(faqs)), gp.json_ld(dataset)])
    out = [head(gp, title, description, canonical, "website", ld, year=y), header(gp, years, y)]
    out.append(crumbs_html(gp, [(n, u.replace(gp.SITE, "")) for n, u in crumbs]))
    out.append(f"<h1>Taiwan Public Holidays {y}: Long Weekends and Leave Planner</h1>")

    lg_sentence = (f"The longest break is the <a href=\"{en_path(y, lg['slug'])}\">{gp.esc(run_en(lg)[0])}</a> "
                   f"({tt(gp, lg['start'])} to {tt(gp, lg['end'])}, {lg['length']} days in a row)." if lg
                   else "There are no breaks of 3 or more days.")
    out.append(f"""<p class="lead">Taiwan's {y} government office calendar has {ym['total_days']} days: {ym['off_days']} non-working days (weekends included) and {ym['work_days']} working days. The official calendar lists {len(ym['holidays'])} holiday entries (including {ym['buja_count']} compensatory days off and {ym['weekend_holiday_count']} holidays that fall on weekends) and {len(runs)} long weekends of 3 or more days. {lg_sentence} {gp.esc(makeup_sentence(gp, ym, since))}</p>""")
    out.append(f"""<div class="stats">
<div class="stat"><b>{len(ym['holidays'])}</b>holiday entries</div>
<div class="stat"><b>{len(runs)}</b>long weekends (3+ days)</div>
<div class="stat"><b>{lg['length'] if lg else 0}</b>days, longest break</div>
<div class="stat"><b>{len(ym['makeup'])}</b>make-up workdays</div>
<div class="stat"><b>{ym['work_days']}</b>working days</div>
</div>""")
    out.append(f'<p class="note">Want a printable one-page calendar? <a href="{poster.poster_path(y, "en")}" target="_blank" rel="noopener">Taiwan {y} calendar (A4, PNG / PDF download)</a>.</p>')

    if runs:
        items = []
        for r in runs:
            n, _ = run_en(r)
            items.append(f'<li><a class="run-name" href="{en_path(y, r["slug"])}">{gp.esc(n)}</a>'
                         f'<span class="run-days">{r["length"]} days</span>'
                         f'<span class="run-dates">{tt(gp, r["start"])} to {tt(gp, r["end"])} · {gp.esc(", ".join(run_names_en(r)))}</span></li>')
        trailing = ""
        if ym["leads_into_next_year"]:
            last = gp.parse_compact(ym["calendar"][-1]["date"])
            trailing = f'<p class="note">The holiday on {tt(gp, last)} continues into early {y + 1}; long weekends here are counted per calendar year, so it is not listed.</p>'
        out.append(f"""<section class="card" aria-labelledby="runs-h">
<h2 id="runs-h">Long weekends in Taiwan, {y} (3+ days)</h2>
<p>A long weekend here means 3 or more consecutive days off, weekends included. Open one for its leave-planning options and a day-by-day table.</p>
<ul class="run-list">
{chr(10).join(items)}
</ul>
{trailing}
</section>""")

    rows = []
    for h in ym["holidays"]:
        d = gp.parse_compact(h["date"])
        run = ym["run_lookup"].get(d)
        n = ym["off_len"].get(d, 1)
        if run:
            cell = f'<a href="{en_path(y, run["slug"])}">{gp.esc(run_en(run)[0])}</a> ({run["length"]} days)'
        elif n >= 2:
            cell = f"{n} days off in a row (with a weekend)"
        else:
            cell = "Single day"
        rows.append(f'<tr><th scope="row">{gp.time_tag(d, d.isoformat())}</th><td>{WEEK3[d.weekday()]}</td>'
                    f'<td class="wrap">{gp.esc(holiday_en(h["description"]))}</td><td>{cell}</td></tr>')
    out.append(f"""<section class="card" aria-labelledby="holidays-h">
<h2 id="holidays-h">Taiwan public holidays {y}: full list</h2>
<p>{len(ym['holidays'])} entries from the official government calendar, including compensatory days off and holidays that fall on weekends (ordinary weekends are not listed).</p>
<div class="table-wrap"><table>
<caption>Taiwan public holidays in {y} (date, weekday, name, long weekend)</caption>
<thead><tr><th scope="col">Date</th><th scope="col">Day</th><th scope="col">Holiday</th><th scope="col">Long weekend</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table></div>
</section>""")

    if ym["makeup"]:
        mrows = "".join(f'<tr><th scope="row">{gp.time_tag(gp.parse_compact(m["date"]), gp.compact_to_iso(m["date"]))}</th>'
                        f'<td>{WEEK3[gp.parse_compact(m["date"]).weekday()]}</td><td class="wrap">Make-up workday</td></tr>' for m in ym["makeup"])
        mk_body = (f'<div class="table-wrap"><table><caption>Make-up workdays in {y}</caption>'
                   f'<thead><tr><th scope="col">Date</th><th scope="col">Day</th><th scope="col">Note</th></tr></thead><tbody>{mrows}</tbody></table></div>')
    else:
        mk_body = f"<p>{gp.esc(makeup_sentence(gp, ym, since))}</p>"
    out.append(f"""<section class="card" aria-labelledby="makeup-h">
<h2 id="makeup-h">Make-up workdays in Taiwan, {y}</h2>
{mk_body}
<p class="note">Machine-readable: <code>{gp.CDN}/{y}/makeup-workdays.json</code> (an empty array <code>[]</code> when there are none).</p>
</section>""")

    if runs or ym["extra_plans"]:
        prow = []
        for r in runs:
            n, _ = run_en(r)
            if not r["plans"]:
                prow.append(f'<tr><th scope="row"><a href="{en_path(y, r["slug"])}">{gp.esc(n)}</a></th><td colspan="4">Working days on both sides exceed {gp.LEAVE_BUDGET}; no bridge plan within {gp.LEAVE_BUDGET} days of leave</td></tr>')
                continue
            p = r["plans"][0]
            leave = [gp.iso_to_date(x) for x in p["leaveDates"]]
            s, e = gp.iso_to_date(p["offRange"]["start"]), gp.iso_to_date(p["offRange"]["end"])
            prow.append(f'<tr><th scope="row"><a href="{en_path(y, r["slug"])}">{gp.esc(n)}</a></th>'
                        f'<td>{p["leaveSpent"]}</td><td>{p["totalDaysOff"]}</td>'
                        f'<td>{", ".join(tt(gp, d) for d in leave)}</td><td>{tt(gp, s, mon_day(s))}–{tt(gp, e, mon_day(e))}</td></tr>')
        out.append(f"""<section class="card" aria-labelledby="leave-h">
<h2 id="leave-h">Leave planner {y}: the best way to extend each break</h2>
<p>Plans come from this site's workday engine (the same algorithm as the <a href="{gp.MCP_DOCS}" rel="noopener noreferrer">MCP server</a>'s <code>optimize_leave</code>): take up to {gp.LEAVE_BUDGET} working days off before or after a holiday to link it to another break. The table shows the best plan per long weekend; each page has up to three.</p>
<div class="table-wrap"><table>
<caption>Best leave plan for each Taiwan long weekend in {y}</caption>
<thead><tr><th scope="col">Long weekend</th><th scope="col">Leave days</th><th scope="col">Days off in a row</th><th scope="col">Leave dates</th><th scope="col">Break</th></tr></thead>
<tbody>
{chr(10).join(prow)}
</tbody></table></div>
</section>""")

    out.append(faq_html(gp, faqs))
    out.append(f"""<section class="card" aria-labelledby="api-h">
<h2 id="api-h">Free data and API for {y}</h2>
<p>All figures come from these JSON files (free, no API key; dates are <code>YYYYMMDD</code>):</p>
<ul class="link-list">
<li><a href="/data/{y}/holidays-en.json">holidays-en.json</a> – {y} public holidays in English (CDN: <code>{gp.CDN}/{y}/holidays-en.json</code>)</li>
<li><a href="/data/{y}/calendar-en.json">calendar-en.json</a> – full-year daily calendar in English (CDN: <code>{gp.CDN}/{y}/calendar-en.json</code>)</li>
<li><a href="/data/{y}/makeup-workdays.json">makeup-workdays.json</a> – make-up workdays</li>
</ul>
<p>For AI agents, the <a href="{gp.MCP_DOCS}" rel="noopener noreferrer">MCP server</a> (<code>{gp.MCP_ENDPOINT}</code>, Streamable HTTP, no auth) provides <code>count_workdays</code>, <code>add_workdays</code>, <code>next_makeup_workday</code>, <code>optimize_leave</code> and <code>find_travel_windows</code>.</p>
<p>More: <a href="/api.html">API docs</a> · <a href="/llms-full.txt">llms-full.txt</a> · <a href="/">interactive calendar (with an English UI)</a></p>
</section>""")

    prev_link = (f'<a href="{en_path(prev_year)}" rel="prev">← Taiwan holidays {prev_year}</a>' if prev_year
                 else f'<span class="disabled">{y - 1} page not generated</span>')
    next_link = (f'<a href="{en_path(next_year)}" rel="next">Taiwan holidays {next_year} →</a>' if next_year
                 else f'<span class="disabled">{y + 1} calendar not yet announced</span>')
    out.append(f'<nav class="pager" aria-label="Previous and next year">{prev_link}{next_link}</nav>')
    out.append(footer(gp))
    return "\n".join(out)


def render_run(gp, ym, run, idx, years, all_by_date):
    y = ym["year"]
    runs = ym["runs"]
    name, label = run_en(run)
    canonical = f"{gp.SITE}{en_path(y, run['slug'])}"
    plans = run["plans"]
    combo = run.get("combo")
    shown = list(plans)
    if combo and len(shown) < gp.PLANS_PER_RUN:
        shown.append(combo)
    best = plans[0] if plans else None
    names = ", ".join(run_names_en(run))

    title = f"{name} {y} Taiwan: {span(run['start'], run['end'])} ({run['length']} days) – Leave Planner｜{gp.SITE_NAME}"
    desc_plan = (f"Best plan: {plan_sentence(gp, best)}." if best
                 else f"Working days on both sides exceed {gp.LEAVE_BUDGET}; no bridge plan within {gp.LEAVE_BUDGET} days of leave.")
    description = (f"Taiwan's {name} {y} runs {mdw(run['start'])} to {mdw(run['end'])}, {run['length']} days in a row ({names}). "
                   f"{desc_plan} Includes a day-by-day table, {len(shown)} leave plan{'s' if len(shown) != 1 else ''} and neighboring long weekends.")
    crumbs = [("Home", f"{gp.SITE}/en/"), (f"{y} holidays", f"{gp.SITE}{en_path(y)}"), (name, canonical)]
    faqs = run_faqs(gp, ym, run, idx)
    ld = "\n".join([gp.json_ld(gp.breadcrumb_ld(crumbs)), gp.json_ld(gp.faq_ld(faqs))])
    out = [head(gp, title, description, canonical, "article", ld, year=y, slug=run["slug"]), header(gp, years, y, run["slug"])]
    out.append(crumbs_html(gp, [(n, u.replace(gp.SITE, "")) for n, u in crumbs]))
    out.append(f"<h1>{gp.esc(name)} {y}: {long_date(run['start'])} to {long_date(run['end'])} ({run['length']} days)</h1>")

    longer = sum(1 for r in runs if r["length"] > run["length"])
    same = sum(1 for r in runs if r["length"] == run["length"]) - 1
    if longer == 0:
        rank = f"the longest break of {y}" + (f" (tied with {plural(same, 'other')})" if same else "")
    else:
        rank = f"number {longer + 1} by length among the {len(runs)} long weekends of {y}" + (f" (tied with {plural(same, 'other')})" if same else "")
    lead_plan = f"Best way to extend it: {plan_sentence(gp, best)}." if best else ""
    out.append(f"""<p class="lead">Taiwan's {gp.esc(name)} {y} runs from {tt(gp, run['start'])} to {tt(gp, run['end'])}: {run['length']} days off in a row ({run['weekend_days']} weekend days plus {run['length'] - run['weekend_days']} weekday holidays: {gp.esc(names)}). It is {rank}. {lead_plan}</p>""")

    rows = []
    for en in run["entries"]:
        d = gp.parse_compact(en["date"])
        rows.append(f'<tr class="is-off"><th scope="row">{gp.time_tag(d, d.isoformat())}</th><td>{WEEK3[d.weekday()]}</td>'
                    f'<td class="wrap">{gp.esc(holiday_en(en["description"]) if en["description"] else "Weekend")}</td></tr>')
    out.append(f"""<section class="card" aria-labelledby="dates-h">
<h2 id="dates-h">Every day of the {gp.esc(name)} {y}</h2>
<div class="table-wrap"><table>
<caption>{gp.esc(name)} days off ({span(run['start'], run['end'])}, {run['length']} days)</caption>
<thead><tr><th scope="col">Date</th><th scope="col">Day</th><th scope="col">Holiday</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table></div>
</section>""")

    if shown:
        blocks = "\n".join(plan_html(gp, i, p, name) for i, p in enumerate(shown))
        out.append(f"""<section class="card" aria-labelledby="plans-h">
<h2 id="plans-h">How to extend the {gp.esc(name)} {y}: {len(shown)} leave plan{'s' if len(shown) != 1 else ''}</h2>
<p>Plans 1 and 2 come from this site's workday engine (same as the MCP <code>optimize_leave</code>): take working days off before or after the break to link it to another weekend or holiday. {'Plan 3 combines both sides.' if combo and len(shown) == gp.PLANS_PER_RUN else ''}</p>
{blocks}
</section>""")
    else:
        out.append(f"""<section class="card" aria-labelledby="plans-h">
<h2 id="plans-h">Leave plans for the {gp.esc(name)} {y}</h2>
<p>Working days on both sides of the {gp.esc(name)} exceed {gp.LEAVE_BUDGET}, so no plan within {gp.LEAVE_BUDGET} days of leave links it to another break. You can still take leave directly before or after it.</p>
</section>""")

    t_start, t_end, t_rows = day_table(gp, ym, run, best, all_by_date)
    out.append(f"""<section class="card" aria-labelledby="daily-h">
<h2 id="daily-h">Day by day around the {gp.esc(name)} ({span(t_start, t_end)})</h2>
<p>Covers the full weeks around the break{' and Plan 1' if best else ''}: <span class="badge badge-off">Day off</span> is an official day off or weekend, <span class="badge badge-leave">Leave</span> is a day Plan 1 suggests you take off, <span class="badge badge-work">Work</span> is a normal working day.</p>
<div class="table-wrap"><table>
<caption>Daily status, {span(t_start, t_end)}</caption>
<thead><tr><th scope="col">Date</th><th scope="col">Day</th><th scope="col">Status</th><th scope="col">Note</th></tr></thead>
<tbody>
{t_rows}
</tbody></table></div>
</section>""")

    prev_run = runs[idx - 1] if idx > 0 else None
    next_run = runs[idx + 1] if idx + 1 < len(runs) else None
    prev_link = (f'<a href="{en_path(y, prev_run["slug"])}" rel="prev">← {gp.esc(run_en(prev_run)[0])} {span(prev_run["start"], prev_run["end"])} ({prev_run["length"]} days)</a>'
                 if prev_run else f'<span class="disabled">The {gp.esc(name)} is the first long weekend of {y}</span>')
    next_link = (f'<a href="{en_path(y, next_run["slug"])}" rel="next">{gp.esc(run_en(next_run)[0])} {span(next_run["start"], next_run["end"])} ({next_run["length"]} days) →</a>'
                 if next_run else f'<span class="disabled">The {gp.esc(name)} is the last long weekend of {y}</span>')
    out.append(f"""<section class="card" aria-labelledby="neighbors-h">
<h2 id="neighbors-h">Neighboring long weekends in {y}</h2>
<nav class="pager" aria-label="Previous and next long weekend">{prev_link}{next_link}</nav>
<p>Taiwan has {len(runs)} long weekends of 3 or more days in {y}. See the full list, holiday table and make-up workdays on the <a href="{en_path(y)}">Taiwan holidays {y}</a> page.</p>
</section>""")
    out.append(faq_html(gp, faqs))
    out.append(f"""<section class="card" aria-labelledby="more-h">
<h2 id="more-h">Data and API</h2>
<ul class="link-list">
<li><a href="{en_path(y)}">Taiwan public holidays {y}: overview</a></li>
<li><a href="/data/{y}/holidays-en.json">{y} public holidays JSON (English)</a> (CDN: <code>{gp.CDN}/{y}/holidays-en.json</code>)</li>
<li><a href="/api.html">JSON API docs</a> · <a href="/llms-full.txt">llms-full.txt</a> · <a href="{gp.MCP_DOCS}" rel="noopener noreferrer">MCP server for AI agents</a></li>
<li><a href="{poster.poster_path(y, 'en')}">Printable {y} calendar (PNG / PDF)</a></li>
</ul>
</section>""")
    out.append(footer(gp))
    return "\n".join(out)


def render_home(gp, years, loaded, since):
    """/en/：英文入口頁。數字取最新年度，其餘導向各年度頁。"""
    canonical = f"{gp.SITE}/en/"
    latest = years[-1]
    first = years[0]
    models = {y: gp.build_year(y, loaded) for y in years}
    title = f"Taiwan Public Holidays {first}–{latest}: Calendar, Long Weekends & Leave Planner｜{gp.SITE_NAME}"
    description = (f"Free Taiwan public holidays calendar for {', '.join(str(y) for y in years)}: official holiday dates, long weekends, "
                   f"make-up workdays, leave-planning tips, a printable one-page calendar, a JSON API and an MCP server for AI agents.")
    faqs = []
    ym = models[latest]
    faqs.append((
        f"What are Taiwan's public holidays in {latest}?",
        f"Taiwan's official {latest} calendar lists {len(ym['holidays'])} holiday entries and {len(ym['runs'])} long weekends of 3 or more days. "
        f"Open the {latest} page for the full list with dates.",
    ))
    lny = next((r for r in ym["runs"] if r["slug"].startswith("lunar-new-year")), None)
    if lny:
        faqs.append((
            f"When is Chinese (Lunar) New Year {latest} in Taiwan?",
            f"The {latest} Lunar New Year holiday in Taiwan runs from {long_date(lny['start'])} to {long_date(lny['end'])}, {lny['length']} days in a row.",
        ))
    faqs.append((f"Does Taiwan have make-up workdays in {latest}?", makeup_sentence(gp, ym, since)))
    faqs.append((
        "How do I plan time off around Taiwan's holidays?",
        "Each long-weekend page shows up to three leave plans that link the break to nearby weekends, and the year page has a table of the best plan per holiday. "
        "The same engine is available to AI agents through the MCP server.",
    ))
    faqs.append((
        "Is there a free Taiwan holidays API?",
        f"Yes. Static JSON files need no API key: {gp.CDN}/<year>/holidays-en.json (public holidays) and {gp.CDN}/<year>/calendar-en.json (full-year calendar). "
        f"Data is CC BY 4.0, from the DGPA Executive Yuan calendar on data.gov.tw (dataset 14718).",
    ))
    site_ld = {
        "@context": "https://schema.org", "@type": "WebSite", "name": gp.SITE_NAME, "url": f"{gp.SITE}/en/",
        "inLanguage": "en", "description": description,
        "publisher": {"@type": "Organization", "name": "Gooliya", "url": "https://www.gooliya.com/"},
    }
    crumbs = [("Home", canonical)]
    ld = "\n".join([gp.json_ld(site_ld), gp.json_ld(gp.breadcrumb_ld(crumbs)), gp.json_ld(gp.faq_ld(faqs))])
    out = [head(gp, title, description, canonical, "website", ld), header(gp, years)]
    out.append("<h1>Taiwan Public Holidays: Calendar, Long Weekends and Leave Planner</h1>")
    out.append(f"""<p class="lead">Official Taiwan public holidays for {', '.join(str(y) for y in years)}, turned into plain-English pages: every long weekend with the best days to take off, make-up workdays, a printable one-page calendar, and free JSON data. Dates come from the Taiwan government's office calendar and are synced monthly.</p>""")
    cards = []
    for y in years:
        m = models[y]
        lg = m["longest"]
        lg_txt = f"Longest break: {gp.esc(run_en(lg)[0])}, {lg['length']} days ({span(lg['start'], lg['end'])})." if lg else ""
        cards.append(f"""<li><a class="run-name" href="{en_path(y)}">Taiwan public holidays {y}</a><span class="run-days">{len(m['runs'])} long weekends</span><span class="run-dates">{lg_txt} {plural(len(m['makeup']), 'make-up workday') if m['makeup'] else 'No make-up workdays.'} · <a href="{poster.poster_path(y, 'en')}" target="_blank" rel="noopener">Printable {y} calendar</a></span></li>""")
    out.append(f"""<section class="card" aria-labelledby="years-h">
<h2 id="years-h">Pick a year</h2>
<ul class="run-list">
{chr(10).join(cards)}
</ul>
</section>""")
    out.append(f"""<section class="card" aria-labelledby="tools-h">
<h2 id="tools-h">Tools</h2>
<ul class="link-list">
<li><a href="/">Interactive calendar</a> – month view with a one-click English switch</li>
<li><a href="/api.html">Free JSON API</a> – English files: <code>holidays-en.json</code>, <code>calendar-en.json</code></li>
<li><a href="{gp.MCP_DOCS}" rel="noopener noreferrer">MCP server</a> – workday math and leave planning for AI agents (<code>{gp.MCP_ENDPOINT}</code>)</li>
<li><a href="/calendar/">Subscribe to the .ics calendar</a> (page in Chinese; the feed works in Google, Apple and Outlook calendars)</li>
<li><a href="{gp.GITHUB}" rel="noopener noreferrer">GitHub</a> – source code and data</li>
</ul>
</section>""")
    out.append(faq_html(gp, faqs))
    out.append(footer(gp))
    return "\n".join(out)


def render_en_site(gp, years, loaded, since, all_by_date, lastmod):
    """回傳 (files, sitemap_entries)。files 的 key 為相對路徑。"""
    files = {"en/index.html": render_home(gp, years, loaded, since)}
    sitemap = [(f"{gp.SITE}/en/", lastmod, "weekly", "0.9")]
    for y in years:
        ym = gp.build_year(y, loaded)
        files[f"en/{y}/index.html"] = render_hub(gp, ym, years, since)
        sitemap.append((f"{gp.SITE}{en_path(y)}", lastmod, "monthly", "0.9"))
        for idx, run in enumerate(ym["runs"]):
            files[f"en/{y}/{run['slug']}/index.html"] = render_run(gp, ym, run, idx, years, all_by_date)
            sitemap.append((f"{gp.SITE}{en_path(y, run['slug'])}", lastmod, "monthly", "0.7"))
    return files, sitemap
