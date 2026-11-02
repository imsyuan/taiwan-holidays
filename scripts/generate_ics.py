#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""從 data/ 產生可訂閱的行事曆檔 calendar/tw-holidays.ics（RFC 5545）。

只使用標準函式庫。讀 data/years.json 列出的所有年度（含尚未到來的年度），合併成「單一永久檔」，
訂閱者訂閱一次、之後靠 REFRESH-INTERVAL 自動更新即可。

設計取捨
    * 一天一筆全天事件，不把連假合併成跨日事件：政府臨時調整某一天（例如多一天補假）時，
      單日事件的 UID 不會變，訂閱端只會多／少一筆，不會讓整段連假被改寫或重複。
    * 國定假日：isHoliday 為 true 且有名稱（與 data/<year>/holidays.json 相同，含補假、落在週末的假日）。
      一般週末沒有名稱，不產生事件。
    * 補班日：isHoliday 為 false 且名稱含 調整上班／補行上班／補班（與 makeup-workdays.json 相同），
      標題為「補班：…」。
    * UID：<YYYYMMDD>-holiday@tw-holidays.gooliya.com／<YYYYMMDD>-makeup@tw-holidays.gooliya.com。
    * DTSTAMP 固定為常數：產生器必須冪等（重跑不產生 diff），所以不能放「產生當下時間」。
      訂閱端每次都重新抓整份檔案，內容改變就會更新，不依賴 DTSTAMP。
    * DESCRIPTION 附網址：該日屬於 3 天以上連假且靜態頁存在時指向 /<year>/<slug>/，
      否則指向 /<year>/（有年度頁時）或首頁。

用法：
    python3 scripts/generate_ics.py            # 產生／更新 calendar/tw-holidays.ics
    python3 scripts/generate_ics.py --check    # 只檢查是否過期，過期則以非零碼結束
"""

import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_pages as gp  # noqa: E402  重用連假 slug 對照

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_PATH = ROOT / "calendar" / "tw-holidays.ics"

SITE = gp.SITE
UID_DOMAIN = "tw-holidays.gooliya.com"
CAL_NAME = "台灣國定假日與補班日"
CAL_DESC = ("台灣國定假日（含補假、調整放假）與補班日，資料來自行政院人事行政總處「政府行政機關辦公日曆表」，"
            f"由 {SITE}/calendar/ 提供，資料每週檢查更新。")
PRODID = "-//Gooliya//Taiwan Holidays//ZH-TW"
DTSTAMP = "20260101T000000Z"  # 固定值，確保冪等；見檔頭說明
MAKEUP_PREFIX = "補班："
MAX_OCTETS = 75


# ---------------------------------------------------------------------------
# RFC 5545 工具
# ---------------------------------------------------------------------------

def escape_text(value):
    """TEXT 值轉義：反斜線、分號、逗號、換行（順序不可顛倒，反斜線要先）。"""
    return (str(value).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n"))


def fold_line(line):
    """依 RFC 5545 3.1 折行：每行最多 75 位元組（不含 CRLF），續行以一個空白開頭。

    以 UTF-8 位元組計算，且絕不切在多位元組字元中間。回傳不含結尾 CRLF 的行串列。
    """
    raw = line.encode("utf-8")
    if len(raw) <= MAX_OCTETS:
        return [line]
    out = []
    current = b""
    limit = MAX_OCTETS
    for ch in line:
        b = ch.encode("utf-8")
        if len(current) + len(b) > limit:
            out.append(current.decode("utf-8"))
            current = b" "  # 續行開頭的空白也算進 75 位元組
            limit = MAX_OCTETS
        current += b
    out.append(current.decode("utf-8"))
    return out


def format_date(d):
    return d.strftime("%Y%m%d")


# ---------------------------------------------------------------------------
# 資料與事件
# ---------------------------------------------------------------------------

def load_years():
    with open(DATA_DIR / "years.json", encoding="utf-8") as f:
        return sorted(int(y) for y in json.load(f)["years"])


def load_calendar(year):
    with open(DATA_DIR / f"{year}.json", encoding="utf-8") as f:
        cal = json.load(f)
    cal.sort(key=lambda e: e["date"])
    return cal


def is_makeup(entry):
    return (not entry["isHoliday"]) and any(k in entry["description"] for k in gp.MAKEUP_KEYWORDS)


def is_holiday(entry):
    return bool(entry["isHoliday"]) and bool(entry["description"])


def page_resolver(year, calendar, root=ROOT):
    """回傳 date -> 該日最適合的網站網址（只指向實際存在的靜態頁）。"""
    hub = (root / str(year) / "index.html").is_file()
    by_day = {}
    for run in gp.find_runs(calendar):
        if (root / str(year) / run["slug"] / "index.html").is_file():
            d = run["start"]
            while d <= run["end"]:
                by_day[d] = f"{SITE}/{year}/{run['slug']}/"
                d += timedelta(days=1)

    def resolve(d):
        if d in by_day:
            return by_day[d]
        return f"{SITE}/{year}/" if hub else f"{SITE}/"

    return resolve


def build_events(years=None, root=ROOT):
    """回傳依日期排序的事件 dict 串列：uid、date、kind（holiday／makeup）、summary、description、url。"""
    years = load_years() if years is None else years
    events = []
    for year in years:
        calendar = load_calendar(year)
        resolve = page_resolver(year, calendar, root)
        for e in calendar:
            if is_holiday(e):
                kind, summary = "holiday", e["description"]
            elif is_makeup(e):
                kind, summary = "makeup", MAKEUP_PREFIX + e["description"]
            else:
                continue
            d = gp.parse_compact(e["date"])
            url = resolve(d)
            if kind == "holiday":
                if url == f"{SITE}/":
                    label = "台灣國定假日行事曆"
                elif url == f"{SITE}/{year}/":
                    label = f"{year} 年國定假日與請假攻略"
                else:
                    label = "連假與請假攻略"
                desc = f"{e['description']}（國定假日）\n{label}：{url}"
            else:
                makeup_url = f"{SITE}/{year}/" if (root / str(year) / "index.html").is_file() else f"{SITE}/"
                url = makeup_url
                desc = f"這天要上班（{e['description']}）\n{year} 年假期與補班日：{url}"
            events.append({
                "uid": f"{e['date']}-{kind}@{UID_DOMAIN}",
                "date": d,
                "kind": kind,
                "summary": summary,
                "description": desc,
                "url": url,
            })
    events.sort(key=lambda ev: (ev["date"], ev["kind"]))
    return events


def event_lines(ev):
    return [
        "BEGIN:VEVENT",
        f"UID:{ev['uid']}",
        f"DTSTAMP:{DTSTAMP}",
        f"DTSTART;VALUE=DATE:{format_date(ev['date'])}",
        f"DTEND;VALUE=DATE:{format_date(ev['date'] + timedelta(days=1))}",
        f"SUMMARY:{escape_text(ev['summary'])}",
        f"DESCRIPTION:{escape_text(ev['description'])}",
        f"URL:{ev['url']}",
        f"CATEGORIES:{'國定假日' if ev['kind'] == 'holiday' else '補班日'}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def render_ics(events):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(CAL_NAME)}",
        f"X-WR-CALDESC:{escape_text(CAL_DESC)}",
        "X-WR-TIMEZONE:Asia/Taipei",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:P1D",
    ]
    for ev in events:
        lines.extend(event_lines(ev))
    lines.append("END:VCALENDAR")
    folded = []
    for line in lines:
        folded.extend(fold_line(line))
    return "\r\n".join(folded) + "\r\n"


def render(root=ROOT):
    return render_ics(build_events(root=root))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    content = render().encode("utf-8")
    old = OUT_PATH.read_bytes() if OUT_PATH.exists() else None
    if check:
        if old != content:
            print("calendar/tw-holidays.ics 已過期，請執行 python3 scripts/generate_ics.py")
            sys.exit(1)
        print("calendar/tw-holidays.ics 已是最新。")
        return
    events = content.count(b"BEGIN:VEVENT")
    if old != content:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_bytes(content)
        print(f"已更新 calendar/tw-holidays.ics（{events} 筆事件）")
    else:
        print(f"calendar/tw-holidays.ics 已是最新（{events} 筆事件）。")


if __name__ == "__main__":
    main()
