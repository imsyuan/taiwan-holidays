# Taiwan Holidays API

> 提供台灣國定假日與行政機關辦公日曆的 JSON API 服務

[![Update Calendar](https://github.com/imsyuan/taiwan-holidays/actions/workflows/update-calendar.yml/badge.svg)](https://github.com/imsyuan/taiwan-holidays/actions/workflows/update-calendar.yml)

## 特色

- 🗓️ **完整日曆資料** — 涵蓋每日的上班/放假狀態與節日說明
- 🔄 **自動同步更新** — 透過 GitHub Actions 定期從政府開放資料同步
- 🌐 **CDN 快速存取** — 支援 jsDelivr 全球 CDN 加速
- 📦 **標準化格式** — 統一的 JSON Schema，易於整合

## 快速開始

### API 端點

```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/{year}.json
```

### 使用範例

**JavaScript**
```javascript
const response = await fetch('https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2025.json');
const holidays = await response.json();

// 查詢今天是否放假
const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
const todayInfo = holidays.find(d => d.date === today);
console.log(todayInfo?.isHoliday ? '今天放假！' : '今天要上班');
```

**Python**
```python
import requests

holidays = requests.get(
    'https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2025.json'
).json()

# 篩選所有國定假日
national_holidays = [d for d in holidays if d['isHoliday'] and d['description']]
```

## 資料格式

| 欄位 | 型別 | 說明 |
|------|------|------|
| `date` | `string` | 日期，格式為 `YYYYMMDD` |
| `week` | `string` | 星期幾 (`一` ~ `日`) |
| `isHoliday` | `boolean` | `true` 表示放假，`false` 表示上班 |
| `description` | `string` | 節日名稱或補假說明（一般工作日為空字串）|

### 回應範例

```json
[
  { "date": "20250101", "week": "三", "isHoliday": true, "description": "開國紀念日" },
  { "date": "20250102", "week": "四", "isHoliday": false, "description": "" }
]
```

## 可用資料年份

目前提供 2017 年至 2026 年的資料，每年約於 6 月新增下一年度資料。

## 資料來源與授權

本專案資料取自[政府資料開放平臺](https://data.gov.tw/)之「中華民國政府行政機關辦公日曆表」，依據[政府資料開放授權條款](https://data.gov.tw/license)使用，並以 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 授權釋出。

## 參考

本專案靈感來自 [ruyut/TaiwanCalendar](https://github.com/ruyut/TaiwanCalendar)。
