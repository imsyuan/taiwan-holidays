#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗證 data/ 目錄下的 JSON 資料正確性（供 CI 使用）。

檢查項目：
1. 每年的 5 個檔案都存在且能正確解析 JSON
2. 每筆資料的欄位結構與型別正確
3. date 為合法的 8 位西元日期，且與所屬年份相符
4. 中文版的 lunar 欄位與 compute_lunar 重新計算的結果完全一致
   （防止「公曆被當成農曆」這類換算 bug 再次溜進資料）
5. 英文版檔案使用英文星期、且不含 lunar 欄位

任何一項失敗即印出問題並以非零結束碼退出，讓 CI 變紅、擋下合併。
"""

import json
import sys
from datetime import date as date_cls
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from update_calendar import compute_lunar  # noqa: E402  與產生腳本共用換算邏輯

DATA_DIR = SCRIPT_DIR.parent / "data"

WEEK_ZH = {"一", "二", "三", "四", "五", "六", "日"}
WEEK_EN = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}

errors = []


def err(path, msg):
    errors.append(f"{path.relative_to(DATA_DIR.parent)}: {msg}")


def load(path):
    if not path.exists():
        err(path, "檔案不存在")
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        err(path, f"JSON 解析失敗: {e}")
        return None
    if not isinstance(data, list):
        err(path, "頂層應為 list")
        return None
    return data


def check_date(path, entry, expect_year):
    d = entry.get("date")
    if not (isinstance(d, str) and len(d) == 8 and d.isdigit()):
        err(path, f"date 格式錯誤: {d!r}")
        return None
    y, m, day = int(d[:4]), int(d[4:6]), int(d[6:8])
    try:
        date_cls(y, m, day)
    except ValueError:
        err(path, f"date 非合法日期: {d}")
        return None
    if y != expect_year:
        err(path, f"date 年份 {y} 與檔案年份 {expect_year} 不符: {d}")
    return d


def check_common(path, entry, d):
    if not isinstance(entry.get("isHoliday"), bool):
        err(path, f"{d}: isHoliday 非 bool")
    if not isinstance(entry.get("description", ""), str):
        err(path, f"{d}: description 非字串")


def validate_zh(path, expect_year):
    """中文版：星期為中文，且 lunar 必須與重新計算的結果一致。"""
    data = load(path)
    if data is None:
        return
    for entry in data:
        d = check_date(path, entry, expect_year)
        if d is None:
            continue
        if entry.get("week") not in WEEK_ZH:
            err(path, f"{d}: week 非中文星期 {entry.get('week')!r}")
        check_common(path, entry, d)
        if "lunar" not in entry:
            err(path, f"{d}: 缺少 lunar 欄位")
        else:
            expected = compute_lunar(d)
            if entry["lunar"] != expected:
                err(path, f"{d}: lunar 不一致 stored={entry['lunar']} expected={expected}")


def validate_en(path, expect_year):
    """英文版：星期為英文，且不應包含 lunar 欄位。"""
    data = load(path)
    if data is None:
        return
    for entry in data:
        d = check_date(path, entry, expect_year)
        if d is None:
            continue
        if entry.get("week") not in WEEK_EN:
            err(path, f"{d}: week 非英文星期 {entry.get('week')!r}")
        check_common(path, entry, d)
        if "lunar" in entry:
            err(path, f"{d}: 英文版不應包含 lunar 欄位")


def main():
    year_files = sorted(DATA_DIR.glob("[0-9][0-9][0-9][0-9].json"))
    if not year_files:
        print("❌ 找不到任何 data/<year>.json")
        sys.exit(1)

    for yf in year_files:
        year = int(yf.stem)
        ydir = DATA_DIR / str(year)
        validate_zh(yf, year)
        validate_zh(ydir / "holidays.json", year)
        validate_zh(ydir / "makeup-workdays.json", year)
        validate_en(ydir / "calendar-en.json", year)
        validate_en(ydir / "holidays-en.json", year)

    if errors:
        print(f"❌ 驗證失敗，共 {len(errors)} 個問題：")
        for e in errors[:200]:
            print("  -", e)
        if len(errors) > 200:
            print(f"  ...（其餘 {len(errors) - 200} 個略）")
        sys.exit(1)

    print(f"✅ 驗證通過：{len(year_files)} 個年度、每年 5 個檔案全部正確")


if __name__ == "__main__":
    main()
