## Why

目前專案只把假日資料當成靜態 JSON 透過 CDN 提供，使用者拿到的是「裸資料」——必須自己寫程式判斷工作日、扣補班、推算連假。對 LLM/agent 與 HR/企業而言，真正的痛點不是「查得到哪天放假」，而是「**在這份日曆上做時間決策**」：算工作日、算補班、最佳化請假、找出遊時段。這些運算只靠 `curl` CDN 做不到，也正是台灣資料（含官方公告才有的補班/調移）別人複製不了的價值所在。

把核心抽成「台灣工作日計算引擎」並以 remote MCP server 對外，是讓 agent 與企業能直接消費這份資產的最低成本入口，也為日後（iCal、套件、API、收費）鋪好共用核心。

## What Changes

- 新增一個與框架無關的**純運算核心模組**（workday-engine），不依賴 MCP/HTTP，可被未來的 iCal、npm/pip 套件、REST API 共用。核心吃既有 `data/<year>.json` 的資料形狀，提供：工作日判定、連假偵測、補班查詢、請假最佳化、出遊時段推算。
- 新增一個部署於 **Cloudflare Workers 的 remote MCP server**（薄殼），以 Streamable HTTP transport 暴露首版 4 個工具：
  - `optimize_leave` — 給定年假天數與期間，回傳 CP 值最高的請假組合（哪幾天請、可換得幾天連假）。
  - `count_workdays` / `add_workdays` — 計算兩日期間的工作日數、或自某日起算 N 個工作日落點（自動扣除國定假日**與補班日**）。
  - `next_makeup_workday` — 查詢下一個（或指定期間內所有）補班日。
  - `find_travel_windows` — 給定可請假天數與想要的出遊長度，回傳最佳出遊時段（含建議請假日）；僅提供「時機」，不涉及訂位/旅遊資料。
- MCP server 在執行時**直接讀取與 Worker 一起 bundle 的 `data/*.json`**，不繞 jsDelivr CDN（更快、更穩、資料即時）。
- 公開網站（index.html/app.js）與既有公開 JSON API 維持不變，仍透過 jsDelivr 提供。

## Non-Goals

- **多國資料**：本次僅台灣。多國的分層資料源（官方逐年公告 vs 聚合函式庫）與 `provenance` 標註留待後續 change。
- **旅遊產品**：不串接機票/飯店/景點等任何旅遊資料或 API；`find_travel_windows` 只計算「何時去」，訂位交由 agent 串接其他 MCP。
- **收費 / 計費 / 認證**：本版 MCP 為無狀態、只讀、公開；API key、用量限流、OAuth、付費方案不在範圍，待使用者養成後另議。
- **stdio 版 MCP**：本次先做 remote(Cloudflare)；stdio 薄殼可日後再加（核心模組已預留共用）。
- **改寫前端日曆**：app.js 既有的瀏覽器端 lunar/strategy 渲染不在本次更動範圍。

## Capabilities

### New Capabilities

- `workday-engine`: 與框架無關的純運算核心，輸入既有假日 JSON，提供工作日判定、連假偵測、補班查詢、請假最佳化、出遊時段推算等可被多種出海口共用的計算函式。
- `workday-mcp-server`: 部署於 Cloudflare Workers 的 remote MCP server，讀取 bundle 的假日資料，透過 Streamable HTTP 暴露首版 4 個工具，將 workday-engine 的運算包裝為 agent/HR 可呼叫的介面。

### Modified Capabilities

(none)

## Impact

- Affected specs: 新增 `workday-engine`、`workday-mcp-server` 兩個 capability。
- Affected code:
  - New:
    - mcp/src/engine/index.ts（workday-engine 核心，純函式、無 I/O）
    - mcp/src/engine/types.ts（日曆/結果型別，對齊 data JSON 形狀）
    - mcp/src/index.ts（MCP server 入口，註冊 4 個工具、McpAgent / Streamable HTTP）
    - mcp/src/data.ts（載入 bundle 的 data/*.json，供 server 注入 engine）
    - mcp/wrangler.jsonc（MCP Worker 部署設定）
    - mcp/package.json（MCP 子專案依賴：Cloudflare agents SDK 等）
    - mcp/README.md（MCP 連線方式與工具說明）
  - Modified:
    - README.md（新增 MCP 端點與工具使用說明段落）
  - Removed: (none)
- Data dependency: 讀取既有 data/<year>.json（含 isHoliday、description、補班標記），不改變其格式或產生流程。
- External dependency: Cloudflare Workers（已有 wrangler 設定）、Cloudflare agents SDK（McpAgent / Streamable HTTP transport）。
