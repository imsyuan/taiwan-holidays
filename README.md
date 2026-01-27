# Taiwan Holidays API

> 提供台灣國定假日與行政機關辦公日曆的 JSON API 服務

[![Update Calendar](https://github.com/imsyuan/taiwan-holidays/actions/workflows/update-calendar.yml/badge.svg)](https://github.com/imsyuan/taiwan-holidays/actions/workflows/update-calendar.yml)

## ✨ 特色

- 🗓️ **完整日曆資料** — 涵蓋每日的上班/放假狀態與節日說明
- 🎌 **國定假日清單** — 只列出真正的國定假日（不含週末）
- 💼 **補班日清單** — 快速查詢需要補班的日期
- 🌐 **中英雙語** — 提供英文版本，方便國際化應用
- 🔄 **自動同步更新** — GitHub Actions 定期從政府開放資料同步
- 📦 **CDN 快速存取** — jsDelivr 全球 CDN 加速

## 🔗 API 端點

所有資料都可透過 jsDelivr CDN 存取，以 2025 年為例：

### 完整日曆（中文）
```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2025.json
```

### 國定假日（中文）
```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2025/holidays.json
```

### 國定假日（英文）
```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2025/holidays-en.json
```

### 補班日清單
```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2025/makeup-workdays.json
```

### 完整日曆（英文）
```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2025/calendar-en.json
```

> 💡 其他年份只需將 `2025` 替換為 `2017`~`2026`

## 🚀 使用範例

**JavaScript - 取得國定假日**
```javascript
const holidays = await fetch(
  'https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2025/holidays.json'
).then(r => r.json());

console.log(holidays);
// [{ date: "20250101", week: "三", isHoliday: true, description: "開國紀念日" }, ...]
```

**JavaScript - 英文版國定假日**
```javascript
const holidays = await fetch(
  'https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2025/holidays-en.json'
).then(r => r.json());

console.log(holidays);
// [{ date: "20250101", week: "Wed", isHoliday: true, description: "New Year's Day" }, ...]
```

**Python - 查詢補班日**
```python
import requests

workdays = requests.get(
    'https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2025/makeup-workdays.json'
).json()

print(f"2025 年共有 {len(workdays)} 天需要補班")
```

## 📊 資料格式

| 欄位 | 型別 | 說明 |
|------|------|------|
| `date` | `string` | 日期 (`YYYYMMDD`) |
| `week` | `string` | 星期（中文：`一`~`日` / 英文：`Mon`~`Sun`）|
| `isHoliday` | `boolean` | `true` = 放假，`false` = 上班 |
| `description` | `string` | 節日名稱或說明 |

### 回應範例

**中文版**
```json
{
  "date": "20250101",
  "week": "三",
  "isHoliday": true,
  "description": "開國紀念日"
}
```

**英文版**
```json
{
  "date": "20250101",
  "week": "Wed",
  "isHoliday": true,
  "description": "New Year's Day"
}
```

## 📁 目錄結構

```
data/
├── 2025.json              # 完整日曆（中文）
└── 2025/
    ├── holidays.json      # 國定假日（中文）
    ├── holidays-en.json   # 國定假日（英文）
    ├── makeup-workdays.json # 補班日清單
    └── calendar-en.json   # 完整日曆（英文）
```

## 📅 可用年份

**2017 ~ 2026**（每年約於 6 月新增下一年度資料）

## 📜 資料來源與授權

資料來自[政府資料開放平臺](https://data.gov.tw/)「中華民國政府行政機關辦公日曆表」，依[政府資料開放授權條款](https://data.gov.tw/license)使用，本專案以 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 釋出。

## 🙏 參考

靈感來自 [ruyut/TaiwanCalendar](https://github.com/ruyut/TaiwanCalendar)
