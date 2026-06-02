# Taiwan Holidays API

> 專為台灣軟體工程師與人資 (HR) 量身打造的中華民國國定假日視覺化日曆與 JSON API 服務！提供包含農民曆、補班日與請假攻略的完整行事曆。

[![Update Calendar](https://github.com/imsyuan/taiwan-holidays/actions/workflows/update-calendar.yml/badge.svg)](https://github.com/imsyuan/taiwan-holidays/actions/workflows/update-calendar.yml)
[![](https://data.jsdelivr.com/v1/package/gh/imsyuan/taiwan-holidays/badge?style=rounded)](https://www.jsdelivr.com/package/gh/imsyuan/taiwan-holidays)

## ✨ 特色

- 🗓️ **完整日曆資料** — 涵蓋每日的上班/放假狀態與節日說明
- ✈️ **國定假日清單** — 只列出真正的國定假日（不含週末）
- 💼 **補班日清單** — 快速查詢需要補班的日期
- 🌕 **農民曆支援** — 內建農曆日期、傳統節慶與二十四節氣
- 🌐 **中英雙語** — 提供英文版本，方便國際化應用
- 🔄 **自動同步更新** — GitHub Actions 定期從政府開放資料同步
- 📦 **CDN 快速存取** — jsDelivr 全球 CDN 加速

## 🔗 API 端點

所有資料都可透過 jsDelivr CDN 存取，以 2026 年為例：

### 完整日曆（中文）
```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2026.json
```

### 國定假日（中文）
```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2026/holidays.json
```

### 國定假日（英文）
```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2026/holidays-en.json
```

### 補班日清單
```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2026/makeup-workdays.json
```

### 完整日曆（英文）
```
https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2026/calendar-en.json
```

> 💡 其他年份只需將 `2026` 替換為 `2017`~`2026`

## 🚀 使用範例

**JavaScript - 取得國定假日**
```javascript
const holidays = await fetch(
  'https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2026/holidays.json'
).then(r => r.json());

console.log(holidays);
// [{ date: "20260101", week: "三", isHoliday: true, description: "開國紀念日" }, ...]
```

**JavaScript - 英文版國定假日**
```javascript
const holidays = await fetch(
  'https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2026/holidays-en.json'
).then(r => r.json());

console.log(holidays);
// [{ date: "20260101", week: "Wed", isHoliday: true, description: "New Year's Day" }, ...]
```

**Python - 查詢補班日**
```python
import requests

workdays = requests.get(
    'https://cdn.jsdelivr.net/gh/imsyuan/taiwan-holidays/data/2026/makeup-workdays.json'
).json()

print(f"2026 年共有 {len(workdays)} 天需要補班")
```

## 🤖 MCP Server（台灣工作日計算引擎）

除了裸 JSON，本專案還提供一個 **remote MCP server**，讓 LLM／agent 與 HR／企業可以直接在台灣行事曆上「做時間決策」，而不只是查哪天放假。原始碼在 [`mcp/`](mcp/)，部署於 Cloudflare Workers，透過 Streamable HTTP 對外。

**正式端點（無需認證，公開唯讀）：**

```
https://mcp.tw-holidays.gooliya.com/mcp
```

> 💡 MCP server 內建運算邏輯，並直接讀取與 Worker 一起 bundle 的 `data/*.json`，不在執行時繞 jsDelivr。

### 如何使用

連上後就能用自然語言問：「2026 我有 5 天年假怎麼請最划算？」「今天起算 10 個工作日是哪天？」「下一個補班日？」

**Claude.ai（網頁／桌面）— 自訂 Connector**

1. Settings → Connectors → **Add custom connector**
2. Name 填 `Taiwan Workday`，URL 填上面的正式端點
3. 在對話中啟用該 connector 即可（需支援自訂 connector 的方案）

**Claude Code（CLI）**

```bash
claude mcp add --transport http taiwan-workday https://mcp.tw-holidays.gooliya.com/mcp
```

**MCP Inspector（除錯／探索）**

```bash
npx @modelcontextprotocol/inspector
# Transport 選 Streamable HTTP，URL 填正式端點
```

**其他 MCP client／agent**：transport 選 Streamable HTTP，指向同一網址即可。

### 工具一覽

| 工具 | 用途 | 輸入 | 輸出 |
| --- | --- | --- | --- |
| `count_workdays` | 區間工作日數（自動扣假日、補班計入工作日） | `{ start, end }` | `{ workdays, holidays, makeupWorkdays }` |
| `add_workdays` | 自某日起算第 N 個工作日（負值往回，起始日不計） | `{ from, workdays }` | `{ date }` |
| `next_makeup_workday` | 下一個補班日，或區間內所有補班日 | `{ from? , range? }` | `{ next, all? }` |
| `optimize_leave` | 請假最佳化，依「每請一天換幾天連假」排序 | `{ year, annualLeaveDays, range? }` | `LeavePlan[]` |
| `find_travel_windows` | 最佳出遊時段（只算時機，不含訂位） | `{ year, annualLeaveDays, minTripLength, range? }` | `TravelWindow[]` |

日期一律使用 `YYYY-MM-DD`。年份不可用回 `{ error: "year_unavailable", availableYears }`，輸入錯誤回 `{ error: "invalid_input", detail }`。

### 本地開發

```bash
cd mcp
npm install
npm test             # 執行 workday-engine 單元測試
npm run dev          # wrangler dev，本地端點 http://localhost:8799/mcp
npm run deploy       # 部署到 Cloudflare（需登入；CI 用 CLOUDFLARE_API_TOKEN）
```

資料每月更新或 `mcp/` 有改動時，GitHub Action 會自動重新部署。完整工具契約與連線說明見 [`mcp/README.md`](mcp/README.md)。

## 📊 資料格式

| 欄位 | 型別 | 說明 |
|------|------|------|
| `date` | `string` | 日期 (`YYYYMMDD`) |
| `week` | `string` | 星期（中文：`一`~`日` / 英文：`Mon`~`Sun`）|
| `isHoliday` | `boolean` | `true` = 放假，`false` = 上班 |
| `description` | `string` | 節日名稱或說明 |
| `lunar` | `object` | 農曆資訊物件（包含農曆日期、傳統節日及節氣），若無對應轉換則為 `null` |
| ↳ `date` | `string` | 農曆日期（如 `正月初一`、`十二月廿九`） |
| ↳ `festivals` | `array` | 農曆傳統節日陣列（如 `["春節"]`），無節日則為空陣列 |
| ↳ `solarTerm` | `string` | 農曆二十四節氣（如 `立春`），若當日無節氣則為 `null` |

### 回應範例

**中文版**
```json
{
  "date": "20260101",
  "week": "三",
  "isHoliday": true,
  "description": "開國紀念日",
  "lunar": {
    "date": "十二月初二",
    "festivals": [],
    "solarTerm": null
  }
}
```

**英文版**
```json
{
  "date": "20260101",
  "week": "Wed",
  "isHoliday": true,
  "description": "New Year's Day",
  "lunar": {
    "date": "十二月初二",
    "festivals": [],
    "solarTerm": null
  }
}
```

## 📁 目錄結構

```
data/
├── 2026.json              # 完整日曆（中文）
└── 2026/
    ├── holidays.json      # 國定假日（中文）
    ├── holidays-en.json   # 國定假日（英文）
    ├── makeup-workdays.json # 補班日清單
    └── calendar-en.json   # 完整日曆（英文）
```

## 📅 可用年份

**2017 ~ 2026**（每年約於 6 月新增下一年度資料）

## 📜 授權聲明 (License)

本專案採用**雙授權**：

- **程式碼**（網站前端、資料產生腳本等）採用 **[MIT License](LICENSE)** 授權。
- **資料**（`data/` 目錄下的 JSON）原始資料使用[政府資料開放授權條款－第1版](https://data.gov.tw/license)授權，依照第三條第二項要求標示出處為[政府資料開放平台](https://data.gov.tw/)（資料集 [14718](https://data.gov.tw/dataset/14718)），且依第四條第二項說明使用「創用CC授權 姓名標示 4.0 國際版本（CC BY 4.0）」授權釋出。

## 🙏 參考

- 資料來源：[政府資料開放平台](https://data.gov.tw/) — [中華民國政府行政機關辦公日曆表](https://data.gov.tw/dataset/14718)
- 靈感來自 [ruyut/TaiwanCalendar](https://github.com/ruyut/TaiwanCalendar)
