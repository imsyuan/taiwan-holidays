#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台灣國定假日資料更新腳本
從政府資料開放平台下載辦公日曆表 CSV 並轉換為多種 JSON 格式
"""

import csv
import json
import os
import re
from datetime import datetime
from io import StringIO
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import unquote, quote, urlparse, urlunparse, parse_qs, urlencode

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

WEEK_EN_MAP = {
    "日": "Sun", "一": "Mon", "二": "Tue", "三": "Wed",
    "四": "Thu", "五": "Fri", "六": "Sat"
}

# 節日中英對照表
HOLIDAY_EN_MAP = {
    "開國紀念日": "New Year's Day",
    "補假": "Compensatory Leave",
    "小年夜": "Lunar New Year's Eve Eve",
    "農曆除夕": "Lunar New Year's Eve",
    "春節": "Lunar New Year",
    "調整上班": "Make-up Workday",
    "補行上班": "Make-up Workday",
    "調整放假": "Adjusted Holiday",
    "放假": "Holiday",
    "和平紀念日": "Peace Memorial Day",
    "兒童節及民族掃墓節": "Children's Day & Tomb Sweeping Day",
    "兒童節": "Children's Day",
    "民族掃墓節": "Tomb Sweeping Day",
    "端午節": "Dragon Boat Festival",
    "中秋節": "Mid-Autumn Festival",
    "國慶日": "National Day",
    "彈性放假": "Flexible Holiday",
    "孔子誕辰紀念日": "Confucius Birthday",
    "臺灣光復暨金門古寧頭大捷紀念日": "Taiwan Retrocession Day",
    "臺灣光復節": "Taiwan Retrocession Day",
    "行憲紀念日": "Constitution Day",
}


def get_csv_urls():
    """從政府資料平台 API 取得 CSV 檔案 URL 列表"""
    print("正在取得資料來源列表...")
    
    req = Request(DATA_GOV_API, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    
    csv_urls = {}
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
        
        match = re.search(r"(\d{3})年", resource_name)
        if match:
            roc_year = int(match.group(1))
            ad_year = roc_year + 1911
            csv_urls[ad_year] = url
    
    return csv_urls


def download_csv(url):
    """下載 CSV 並處理編碼"""
    print(f"  下載中: {url[:80]}...")
    
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    encoded_query = urlencode(query_params, doseq=True, safe='')
    safe_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                           parsed.params, encoded_query, parsed.fragment))
    
    req = Request(safe_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as response:
        content = response.read()
    
    for encoding in ["utf-8-sig", "utf-8", "big5", "cp950"]:
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    
    raise ValueError("無法解碼 CSV 檔案")


from lunar_python import Lunar

def s2t(text):
    if not text:
        return text
    mapping = {
        '春节': '春節', '元宵节': '元宵節', '清明节': '清明節', '端午节': '端午節', '中秋节': '中秋節', 
        '重阳节': '重陽節', '除夕': '除夕', '七夕节': '七夕', '腊八节': '臘八節', '小年': '小年',
        '正月': '正月', '腊月': '臘月', '冬月': '冬月', '闰': '閏',
        '立春': '立春', '雨水': '雨水', '惊蛰': '驚蟄', '春分': '春分', '清明': '清明', '谷雨': '穀雨',
        '立夏': '立夏', '小满': '小滿', '芒种': '芒種', '夏至': '夏至', '小暑': '小暑', '大暑': '大暑',
        '立秋': '立秋', '处暑': '處暑', '白露': '白露', '秋分': '秋分', '寒露': '寒露', '霜降': '霜降',
        '立冬': '立冬', '小雪': '小雪', '大雪': '大雪', '冬至': '冬至', '小寒': '小寒', '大寒': '大寒',
        '初一': '初一', '初二': '初二', '初三': '初三', '初四': '初四', '初五': '初五',
        '初六': '初六', '初七': '初七', '初八': '初八', '初九': '初九', '初十': '初十',
        '十一': '十一', '十二': '十二', '十三': '十三', '十四': '十四', '十五': '十五',
        '十六': '十六', '十七': '十七', '十八': '十八', '十九': '十九', '二十': '二十',
        '廿一': '廿一', '廿二': '廿二', '廿三': '廿三', '廿四': '廿四', '廿5': '廿五',
        '廿六': '廿六', '廿七': '廿七', '廿八': '廿八', '廿九': '廿九', '三十': '三十',
        '劳动节': '勞動節', '国庆节': '國慶節', '妇女节': '婦女節', '青年节': '青年節',
        '儿童节': '兒童節', '建军节': '建軍節', '教师节': '教師節', '记者节': '記者節',
        '父亲节': '父親節', '母亲节': '母親節', '万圣节': '萬聖節', '圣诞节': '聖誕節'
    }
    
    # Word replacements first
    words = {
        '春节': '春節', '元宵节': '元宵節', '清明节': '清明節', '端午节': '端午節', '中秋节': '中秋節', 
        '重阳节': '重陽節', '七夕节': '七夕', '腊八节': '臘八節', '惊蛰': '驚蟄', '谷雨': '穀雨',
        '小满': '小滿', '芒种': '芒種', '处暑': '處暑', '劳动节': '勞動節', '国庆节': '國慶節',
        '妇女节': '婦女節', '青年节': '青年節', '儿童节': '兒童節', '建军节': '建軍節', '教师节': '教師節',
        '记者节': '記者節'
    }
    
    for s, t in words.items():
        text = text.replace(s, t)
        
    # Character replace
    res = ''
    for char in text:
        res += mapping.get(char, char)
    
    import re
    res = re.sub(r'节', '節', res)
    res = re.sub(r'惊', '驚', res)
    res = re.sub(r'蛰', '蟄', res)
    res = re.sub(r'谷', '穀', res)
    res = re.sub(r'满', '滿', res)
    res = re.sub(r'种', '種', res)
    res = re.sub(r'处', '處', res)
    res = re.sub(r'岁', '歲', res)
    res = re.sub(r'龙', '龍', res)
    res = re.sub(r'腊', '臘', res)
    return res

def convert_csv_to_json(csv_content):
    """將 CSV 內容轉換為標準 JSON 格式，並加入農曆資訊"""
    reader = csv.DictReader(StringIO(csv_content))
    
    result = []
    for row in reader:
        date_value = row.get("西元日期", row.get("date", ""))
        week_value = row.get("星期", row.get("week", ""))
        holiday_value = row.get("是否放假", row.get("isHoliday", ""))
        desc_value = row.get("備註", row.get("description", ""))
        
        date_str = str(date_value).replace("/", "").replace("-", "")
        if len(date_str) != 8:
            continue
        
        week = WEEK_MAP.get(str(week_value).strip(), week_value)
        
        holiday_str = str(holiday_value).strip()
        if holiday_str in ["2", "是", "true", "True", "1"]:
            is_holiday = True
        elif holiday_str in ["0", "否", "false", "False"]:
            is_holiday = False
        else:
            is_holiday = holiday_str == "2"
        
        description = str(desc_value).strip() if desc_value else ""
        
        # Calculate Lunar Details
        lunar_dict = None
        try:
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            
            lunar = Lunar.fromYmd(year, month, day)
            
            festivals = [s2t(f) for f in lunar.getFestivals()]
            jieQi = s2t(lunar.getJieQi())
            
            lunar_dict = {
                "date": s2t(f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"),
                "festivals": festivals,
                "solarTerm": jieQi if jieQi else None
            }
        except Exception as e:
            print(f"Error calculating lunar date for {date_str}: {e}")
        
        result.append({
            "date": date_str,
            "week": week,
            "isHoliday": is_holiday,
            "description": description,
            "lunar": lunar_dict
        })
    
    return result


def generate_holidays_only(data):
    """生成只包含國定假日的資料（排除一般週末）"""
    return [d for d in data if d["isHoliday"] and d["description"]]


def generate_workdays(data):
    """生成補班日清單"""
    workday_keywords = ["調整上班", "補行上班", "補班"]
    return [d for d in data if not d["isHoliday"] and 
            any(kw in d["description"] for kw in workday_keywords)]


def translate_to_english(data):
    """將資料轉換為英文版"""
    result = []
    for d in data:
        desc_en = HOLIDAY_EN_MAP.get(d["description"], d["description"])
        # 如果沒有直接對應，嘗試部分匹配
        if desc_en == d["description"] and d["description"]:
            for zh, en in HOLIDAY_EN_MAP.items():
                if zh in d["description"]:
                    desc_en = en
                    break
        
        result.append({
            "date": d["date"],
            "week": WEEK_EN_MAP.get(d["week"], d["week"]),
            "isHoliday": d["isHoliday"],
            "description": desc_en
        })
    return result


def save_json(data, filepath, description=""):
    """儲存 JSON 檔案"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    desc = f" ({description})" if description else ""
    print(f"    ✓ {filepath.name}: {len(data)} 筆{desc}")


def process_year(year, csv_content):
    """處理單一年份的所有資料格式"""
    json_data = convert_csv_to_json(csv_content)
    
    if not json_data:
        print(f"  警告: {year} 年沒有有效資料")
        return
    
    # 建立年份子目錄
    year_dir = DATA_DIR / str(year)
    
    # 1. 完整日曆資料
    save_json(json_data, DATA_DIR / f"{year}.json", "完整日曆")
    
    # 2. 只有國定假日
    holidays_only = generate_holidays_only(json_data)
    save_json(holidays_only, year_dir / "holidays.json", "國定假日")
    
    # 3. 補班日清單
    workdays = generate_workdays(json_data)
    save_json(workdays, year_dir / "makeup-workdays.json", "補班日")
    
    # 4. 英文版 - 完整日曆
    en_data = translate_to_english(json_data)
    save_json(en_data, year_dir / "calendar-en.json", "英文完整日曆")
    
    # 5. 英文版 - 只有國定假日
    en_holidays = translate_to_english(holidays_only)
    save_json(en_holidays, year_dir / "holidays-en.json", "英文國定假日")


def main():
    """主程式"""
    print("=" * 60)
    print("🇹🇼 台灣國定假日資料更新")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        csv_urls = get_csv_urls()
        print(f"找到 {len(csv_urls)} 個年度的資料\n")
        
        for year in sorted(csv_urls.keys()):
            url = csv_urls[year]
            print(f"📅 處理 {year} 年資料:")
            
            try:
                csv_content = download_csv(url)
                process_year(year, csv_content)
            except Exception as e:
                print(f"  ❌ 錯誤: {e}")
        
        print("\n" + "=" * 60)
        print("✅ 更新完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        raise


if __name__ == "__main__":
    main()
