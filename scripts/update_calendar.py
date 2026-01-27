#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台灣國定假日資料更新腳本
從政府資料開放平台下載辦公日曆表 CSV 並轉換為 JSON 格式
"""

import csv
import json
import os
import re
from datetime import datetime
from io import StringIO
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import unquote, quote

# 資料來源頁面
DATA_GOV_API = "https://data.gov.tw/api/v2/rest/dataset/14718"

# 輸出目錄
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"

# 星期對應表
WEEK_MAP = {
    "0": "日", "1": "一", "2": "二", "3": "三",
    "4": "四", "5": "五", "6": "六",
    "日": "日", "一": "一", "二": "二", "三": "三",
    "四": "四", "五": "五", "六": "六"
}


def get_csv_urls():
    """從政府資料平台 API 取得 CSV 檔案 URL 列表"""
    print("正在取得資料來源列表...")
    
    req = Request(DATA_GOV_API, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    
    csv_urls = {}
    # API 回傳的是 result.distribution
    result = data.get("result", {})
    distributions = result.get("distribution", [])
    
    for dist in distributions:
        resource_format = dist.get("resourceFormat", "")
        if resource_format.upper() != "CSV":
            continue
        
        resource_name = dist.get("resourceDescription", "")
        url = dist.get("resourceDownloadUrl", "")
        
        if not url or "Google" in resource_name:
            continue
        
        # 從檔名解析年份（民國年）
        match = re.search(r"(\d{3})年", resource_name)
        if match:
            roc_year = int(match.group(1))
            ad_year = roc_year + 1911
            # 只保留最新的版本（後面的會覆蓋前面的）
            csv_urls[ad_year] = url
    
    return csv_urls


def download_csv(url):
    """下載 CSV 並處理編碼"""
    print(f"  下載中: {url[:80]}...")
    
    # 處理 URL 中的非 ASCII 字元（確保正確編碼）
    # 先解碼再重新編碼以處理 URL 中可能的中文字元
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
    parsed = urlparse(url)
    # 重新編碼查詢參數
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    encoded_query = urlencode(query_params, doseq=True, safe='')
    safe_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                           parsed.params, encoded_query, parsed.fragment))
    
    req = Request(safe_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as response:
        content = response.read()
    
    # 嘗試不同編碼
    for encoding in ["utf-8-sig", "utf-8", "big5", "cp950"]:
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    
    raise ValueError("無法解碼 CSV 檔案")


def convert_csv_to_json(csv_content):
    """將 CSV 內容轉換為標準 JSON 格式"""
    reader = csv.DictReader(StringIO(csv_content))
    
    result = []
    for row in reader:
        # 取得各欄位（處理不同的欄位名稱）
        date_value = row.get("西元日期", row.get("date", ""))
        week_value = row.get("星期", row.get("week", ""))
        holiday_value = row.get("是否放假", row.get("isHoliday", ""))
        desc_value = row.get("備註", row.get("description", ""))
        
        # 轉換日期格式
        date_str = str(date_value).replace("/", "").replace("-", "")
        if len(date_str) == 8:
            date_formatted = date_str
        else:
            continue
        
        # 轉換星期
        week = WEEK_MAP.get(str(week_value).strip(), week_value)
        
        # 轉換是否放假
        holiday_str = str(holiday_value).strip()
        if holiday_str in ["2", "是", "true", "True", "1"]:
            is_holiday = True
        elif holiday_str in ["0", "否", "false", "False"]:
            is_holiday = False
        else:
            is_holiday = holiday_str == "2"
        
        # 備註
        description = str(desc_value).strip() if desc_value else ""
        
        result.append({
            "date": date_formatted,
            "week": week,
            "isHoliday": is_holiday,
            "description": description
        })
    
    return result


def save_json(data, year):
    """儲存 JSON 檔案"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    output_path = DATA_DIR / f"{year}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  已儲存: {output_path} ({len(data)} 筆資料)")
    return output_path


def main():
    """主程式"""
    print("=" * 50)
    print("台灣國定假日資料更新")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        csv_urls = get_csv_urls()
        print(f"找到 {len(csv_urls)} 個年度的資料")
        
        for year in sorted(csv_urls.keys()):
            url = csv_urls[year]
            print(f"\n處理 {year} 年資料:")
            
            try:
                csv_content = download_csv(url)
                json_data = convert_csv_to_json(csv_content)
                
                if json_data:
                    save_json(json_data, year)
                else:
                    print(f"  警告: {year} 年沒有有效資料")
            
            except Exception as e:
                print(f"  錯誤: {e}")
        
        print("\n" + "=" * 50)
        print("更新完成!")
        print("=" * 50)
        
    except Exception as e:
        print(f"發生錯誤: {e}")
        raise


if __name__ == "__main__":
    main()
