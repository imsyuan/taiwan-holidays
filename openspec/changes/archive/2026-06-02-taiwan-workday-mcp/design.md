## Context

本專案目前是無後端的靜態網站 + JSON 資料源：`scripts/update_calendar.py` 從政府開放資料產生 `data/<year>.json` 等檔，透過 GitHub Pages 與 jsDelivr CDN 對外。`app.js` 已在瀏覽器端實作連假 run 推導與請假攻略，但這些運算只活在前端、無法被 agent 或外部系統呼叫。

本次要把「在台灣日曆上做時間決策」的運算抽成獨立核心，並以 remote MCP server 對外。最大約束是**盡量維持無後端的低維運特性**：remote MCP 本質上是常駐服務，但選擇 Cloudflare Workers 可 scale-to-zero、無伺服器需修補，是跨過「加後端」這條線的最低成本選項。專案既有 `wrangler.jsonc` 已將 repo 以靜態資產部署到 Workers。

## Goals / Non-Goals

**Goals:**

- 提供與框架無關的純運算核心（workday-engine），可被 MCP、未來的 iCal/套件/API 共用。
- 以 remote MCP server 暴露首版 4 個工具，讓 LLM/agent 與 HR/企業能直接消費台灣假日運算。
- MCP server 自帶資料、不依賴外部 CDN，回應快且穩定。
- 不改變既有資料格式、產生流程、公開網站與公開 JSON API。

**Non-Goals:**

- 多國資料、`provenance` 標註（後續 change）。
- 旅遊資料/訂位串接；`find_travel_windows` 只算時機。
- 認證、計費、用量限流（本版公開、只讀、無狀態）。
- stdio 版 MCP（核心已預留共用，日後可加）。

## Decisions

### 純運算核心與 MCP 薄殼分離

workday-engine 為純函式模組，輸入「已載入的年度日曆陣列 + 參數」，輸出結構化結果，**不做任何 I/O、不認識 MCP/HTTP**。MCP server 僅負責：載入資料、解析工具參數、呼叫 engine、把結果包成 MCP 回應。
理由：避免 MCP 變成「轉發 JSON 的空殼」——價值在運算邏輯，且核心要能被 iCal/套件/API 重用。
替代方案：直接把運算寫在 MCP handler 裡（被否決，無法重用、難測試）。

### 部署於 Cloudflare Workers，使用 agents SDK 的 McpAgent / Streamable HTTP

remote MCP 以 Cloudflare `agents` SDK 的 `McpAgent` 實作，透過 Streamable HTTP transport 在一個固定路徑（如 `/mcp`）對外。
理由：專案已有 Cloudflare/wrangler 設定，無需新增廠商；Workers scale-to-zero、免維運；agents SDK 原生支援 remote MCP transport，並為日後 OAuth/限流預留路徑。
替代方案：stdio MCP（不符「給企業連的 URL」目標）、自架 Node 伺服器或其他 PaaS（多一個廠商與維運負擔，被否決）。

### Worker 直接讀 bundle 的假日資料，不繞 jsDelivr

`data/<year>.json` 隨 Worker 一起部署（bundle 或 Workers 靜態資產），engine 從本地資料取得，不在執行時 fetch jsDelivr。
理由：省一趟對外網路來回（更快）、不依賴第三方 CDN 可用性、避免 CDN 快取造成資料延遲、不繞圈拿自己的資料。代價是資料更新時 Worker 需重新部署（沿用既有 GitHub Action 即可）。
替代方案：執行時 fetch jsDelivr（多延遲與外部依賴）、放 KV/R2（多一層維運，待需要即時/私有資料時再升級）。公開網站與公開 API 仍照舊用 jsDelivr。

### 工作日判定規則（扣除國定假日與補班日）

「工作日」= 非假日的日子。判定以 `data/<year>.json` 的 `isHoliday` 為準：`isHoliday=true` 為休假（不計工作日）；`isHoliday=false` 即為工作日，**補班日（週末但需上班）因 `isHoliday=false` 自然被計為工作日**。連假 run 為連續 `isHoliday=true` 的區段。
理由：直接沿用既有資料語意，與政府公告一致，補班/調移無需另行演算。

### 首版 4 個工具的輸入輸出契約

工具一律以結構化 JSON 回應（見 Implementation Contract），日期統一用 `YYYY-MM-DD` 字串。
理由：agent 需可機器解析的穩定形狀；與既有 `YYYYMMDD` 內部格式在 engine 邊界做轉換。

### find_travel_windows 只提供時機、不碰旅遊資料

該工具基於連假與請假最佳化，輸出「建議出遊區段 + 要請哪幾天」，明確不串任何機票/飯店/景點來源。
理由：守住資料護城河與無後端特性，避免淪為資源最少的旅遊網站；訂位由 agent 串接其他 MCP 完成。

## Implementation Contract

**對外行為**：部署後存在一個 remote MCP endpoint（Cloudflare Worker 上的固定路徑，預設 `/mcp`，Streamable HTTP transport），MCP client 連線後可列出並呼叫下列 4 個工具。

**工具契約（輸入 / 輸出）**：

- `optimize_leave`
  - 輸入：`{ year: number, annualLeaveDays: number, range?: { start: "YYYY-MM-DD", end: "YYYY-MM-DD" } }`
  - 輸出：依「每請一天年假可換得的連假天數」由高到低排序的方案陣列，每筆 `{ leaveDates: ["YYYY-MM-DD"...], offRange: { start, end }, totalDaysOff: number, leaveSpent: number, efficiency: number }`。`efficiency = totalDaysOff / leaveSpent`。
- `count_workdays`
  - 輸入：`{ start: "YYYY-MM-DD", end: "YYYY-MM-DD" }`（含頭含尾）
  - 輸出：`{ workdays: number, holidays: number, makeupWorkdays: number }`；補班日同時計入 workdays，並於 makeupWorkdays 標示其中幾天屬補班。
- `add_workdays`
  - 輸入：`{ from: "YYYY-MM-DD", workdays: number }`（可為負值往回算）
  - 輸出：`{ date: "YYYY-MM-DD" }` — 自 from 起算第 N 個工作日落點（from 當天若為工作日不計入第 1 天，採「下 N 個工作日」語意）。
- `next_makeup_workday`
  - 輸入：`{ from?: "YYYY-MM-DD", range?: { start, end } }`（預設 from = 查詢當下不可用，需由 client 傳入基準日）
  - 輸出：`{ next: "YYYY-MM-DD" | null, all?: ["YYYY-MM-DD"...] }`；給 range 時回傳該期間所有補班日。
- `find_travel_windows`
  - 輸入：`{ year: number, annualLeaveDays: number, minTripLength: number, range?: { start, end } }`
  - 輸出：建議出遊區段陣列 `{ tripRange: { start, end }, tripLength: number, leaveDates: ["YYYY-MM-DD"...], leaveSpent: number }`，依 `tripLength / leaveSpent` 排序。

**失敗模式**：
- 查詢年份無對應 `data/<year>.json` → 回傳結構化錯誤 `{ error: "year_unavailable", availableYears: [...] }`，不丟未處理例外。
- 日期格式非 `YYYY-MM-DD` 或 range 顛倒（start > end）→ `{ error: "invalid_input", detail: "..." }`。
- `annualLeaveDays` / `workdays` 為非整數或負（add_workdays 允許負）→ 依工具規則回 `invalid_input`。

**驗收標準**：
- workday-engine 可在無 MCP/網路環境下，用 `data/<year>.json` 樣本資料單元測試：`count_workdays` 對已知區間（含跨補班日）回傳正確工作日數；`add_workdays` 對含補班的區間落點正確；`optimize_leave` 對已知連假（如 2026 農曆春節）回傳請 1 天換多天的方案。
- 以 MCP client（如 MCP Inspector）連上部署後的 `/mcp`，可列出 4 個工具並各成功呼叫一次得到上述形狀。
- 既有公開網站與 `data/` JSON 端點行為不變。

**範圍邊界**：
- 範圍內：workday-engine 純函式、4 個 MCP 工具、Cloudflare Worker 部署設定、資料 bundle 載入、README/MCP 說明。
- 範圍外：多國、認證/計費、stdio 版、旅遊資料串接、前端日曆改寫、`update_calendar.py` 與資料格式變更。

## Risks / Trade-offs

- [remote MCP 即引入後端責任] → 選 Cloudflare Workers（scale-to-zero、無伺服器維修），把責任壓到最低；本版無狀態只讀，無資料庫。
- [資料更新需重新部署 Worker] → 沿用既有 GitHub Action 在資料更新後觸發部署；可接受，因更新頻率低（月）。
- [agents SDK / Streamable HTTP 為較新規格，介面可能變動] → 將 transport/註冊邏輯集中在 MCP 薄殼，核心不受影響；升級面侷限於薄殼。
- [`add_workdays` 的「第 N 個工作日」語意易誤解] → 在契約與工具描述明確定義「下 N 個工作日、from 當天不計」，並以單元測試鎖定。
- [年份範圍與前端 `state.availableYears` 硬編碼脫鉤] → engine 以實際存在的 `data/<year>.json` 為準動態判斷，不沿用前端的硬編碼範圍。
