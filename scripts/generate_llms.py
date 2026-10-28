#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""從 data/ 重新產生 llms.txt / llms-full.txt 中「會隨時間過期」的事實區塊。

只使用標準函式庫。做法：在檔案中以標記包住事實區塊，本腳本只取代標記之間的內容，
其餘手寫文字完全不動。

    llms.txt        <!-- facts:begin --> ... <!-- facts:end -->          （精簡版）
    llms-full.txt   <!-- facts-full:begin --> ... <!-- facts-full:end --> （含逐年表）

用法：
    python scripts/generate_llms.py           # 就地更新
    python scripts/generate_llms.py --check   # 只檢查，過期則以非零碼結束（可給 CI 用）
"""

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def parse_date(compact):
    return date(int(compact[:4]), int(compact[4:6]), int(compact[6:8]))


def fmt_md(d, week):
    return f"{d.month}/{d.day}（{week}）"


def fmt_full(d, week):
    return f"{d.year}-{d.month:02d}-{d.day:02d}（{week}）"


def load_year(year):
    with open(DATA_DIR / f"{year}.json", encoding="utf-8") as f:
        calendar = json.load(f)
    with open(DATA_DIR / str(year) / "holidays.json", encoding="utf-8") as f:
        holidays = json.load(f)
    with open(DATA_DIR / str(year) / "makeup-workdays.json", encoding="utf-8") as f:
        makeup = json.load(f)
    return calendar, holidays, makeup


def longest_off_run(calendar):
    """該年內最長連續 isHoliday=true 區段（含週末；不跨年）。同長度取最早者。"""
    best = []
    cur = []
    prev = None
    for e in calendar:
        d = parse_date(e["date"])
        if not e["isHoliday"]:
            cur = []
        elif cur and prev is not None and d - prev == timedelta(days=1):
            cur.append(e)
        else:
            cur = [e]
        prev = d
        if len(cur) > len(best):
            best = list(cur)
    return best


def year_facts(year):
    calendar, holidays, makeup = load_year(year)
    run = longest_off_run(calendar)
    names = []
    for e in run:
        n = e["description"]
        if n and n not in names:
            names.append(n)
    return {
        "year": year,
        "holiday_entries": len(holidays),
        "makeup": [(parse_date(e["date"]), e["week"]) for e in makeup],
        "run_len": len(run),
        "run_start": (parse_date(run[0]["date"]), run[0]["week"]) if run else None,
        "run_end": (parse_date(run[-1]["date"]), run[-1]["week"]) if run else None,
        "run_names": names,
    }


def available_years():
    return sorted(
        int(p.stem) for p in DATA_DIR.glob("[0-9][0-9][0-9][0-9].json")
    )


def run_text(f):
    if not f["run_start"]:
        return "無"
    s, e = f["run_start"], f["run_end"]
    names = "、".join(f["run_names"])
    return f"{fmt_md(*s)}–{fmt_md(*e)}，共 {f['run_len']} 天（含：{names}）"


def makeup_text(f):
    if not f["makeup"]:
        return "無（該年度沒有補班日）"
    return f"{len(f['makeup'])} 天：" + "、".join(fmt_md(d, w) for d, w in f["makeup"])


def render_short(years, facts):
    latest = facts[-1]
    y = latest["year"]
    lines = [
        f"- 資料涵蓋 {years[0]}–{years[-1]} 年（共 {len(years)} 個年度，以 `data/` 目錄實際檔案為準；尚未公布的年度沒有檔案）。",
        f"- 最新年度 {y}：`data/{y}/holidays.json` 共 {latest['holiday_entries']} 筆放假紀錄"
        "（含補假，以及落在週六、週日的國定假日，不等於 "
        f"{latest['holiday_entries']} 個獨立節日，也不等於額外多放的平日）。",
        f"- {y} 年補班日：{makeup_text(latest)}。",
        f"- {y} 年最長連假（連續放假含週末，依資料推算）：{run_text(latest)}。",
        "- 以上數字由 `scripts/generate_llms.py` 從 `data/` 產生；要最新、可驗證的數字請直接讀 JSON 或呼叫 MCP，不要沿用本段文字。",
    ]
    return "\n".join(lines)


def render_full(years, facts):
    lines = [render_short(years, facts), ""]
    lines.append("逐年概況（同樣由 `data/` 產生；「最長連假」指該年內連續放假含週末的最長區段，不跨年計算）：")
    lines.append("")
    lines.append("| 年度 | holidays.json 筆數 | 補班日 | 最長連假 |")
    lines.append("| --- | --- | --- | --- |")
    for f in facts:
        mk = (
            "0"
            if not f["makeup"]
            else f"{len(f['makeup'])}（" + "、".join(fmt_md(d, w) for d, w in f["makeup"]) + "）"
        )
        if f["run_start"]:
            rt = f"{fmt_full(*f['run_start'])} 至 {fmt_full(*f['run_end'])}，{f['run_len']} 天"
        else:
            rt = "無"
        lines.append(f"| {f['year']} | {f['holiday_entries']} | {mk} | {rt} |")
    return "\n".join(lines)


TARGETS = [
    ("llms.txt", "facts", render_short),
    ("llms-full.txt", "facts-full", render_full),
]


def replace_block(text, tag, body):
    pattern = re.compile(
        rf"(<!-- {re.escape(tag)}:begin -->\n).*?(\n<!-- {re.escape(tag)}:end -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"找不到標記 <!-- {tag}:begin --> / <!-- {tag}:end -->")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text, count=1)


def main():
    check = "--check" in sys.argv[1:]
    years = available_years()
    if not years:
        raise SystemExit("data/ 底下找不到任何 <year>.json")
    facts = [year_facts(y) for y in years]

    stale = []
    for filename, tag, renderer in TARGETS:
        path = ROOT / filename
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        new = replace_block(old, tag, renderer(years, facts))
        if new != old:
            stale.append(filename)
            if not check:
                path.write_text(new, encoding="utf-8")
                print(f"已更新 {filename}")

    if check and stale:
        print("以下檔案的事實區塊已過期，請執行 python scripts/generate_llms.py：")
        for s in stale:
            print(f"  - {s}")
        sys.exit(1)
    if not stale:
        print("llms 事實區塊已是最新。")


if __name__ == "__main__":
    main()
