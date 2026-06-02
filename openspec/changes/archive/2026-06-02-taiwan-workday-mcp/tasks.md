## 1. 子專案骨架與資料載入

- [x] 1.1 建立 mcp/ 子專案骨架與 mcp/package.json（含 Cloudflare agents SDK 依賴），落實「純運算核心與 MCP 薄殼分離」：engine 目錄為純函式、server 目錄為薄殼。驗證：`npm install` 於 mcp/ 成功，目錄結構含 mcp/src/engine 與 mcp/src/index.ts，且 engine 不 import 任何 MCP/HTTP 模組（以 grep 檢查無 transport import）。
- [x] 1.2 實作資料載入層 mcp/src/data.ts，落實「Serve calendar data from bundled assets」與「Worker 直接讀 bundle 的假日資料，不繞 jsDelivr」：自隨 Worker bundle 的 data/<year>.json 載入日曆、可用年份由實際存在的檔案動態推導。驗證：單元測試載入 2026 年資料回傳非空陣列，且程式碼無任何 jsDelivr/CDN 的 fetch URL（grep 檢查）。

## 2. workday-engine 純運算核心

- [x] 2.1 實作 Workday determination from calendar data：依 isHoliday 判定某日是否為工作日，補班日（isHoliday=false）計為工作日，落實「工作日判定規則（扣除國定假日與補班日）」。驗證：單元測試對一般工作日、國定假日、補班日三種輸入各回傳正確判定。
- [x] 2.2 實作 Count workdays in a date range：對含頭含尾區間回傳 { workdays, holidays, makeupWorkdays }，補班日計入 workdays 並另行標示。驗證：以含 1 國定假日 + 1 補班日的 7 日區間測試，斷言 workdays=6、holidays=1、makeupWorkdays=1。
- [x] 2.3 實作 Add workdays to a date：自起始日起算第 N 個工作日（起始日不計、負值往回），跳過所有非工作日。驗證：單元測試「週五 +1 工作日 = 下週一」與一個跨補班日的案例。
- [x] 2.4 實作 Identify makeup workdays：回傳基準日起最近一個補班日、或指定區間內所有補班日（升冪）。驗證：單元測試對含已知補班日的資料回傳正確日期，無補班時回傳 null。
- [x] 2.5 實作 Optimize annual leave：給定年假天數與選填區間，回傳依 efficiency（總休假/請假天數）降冪排序的請假方案。驗證：以 2026 農曆春節資料測試，斷言存在「請 1 天換多天」且 efficiency 計算正確的方案。
- [x] 2.6 實作 Find travel windows，落實「find_travel_windows 只提供時機、不碰旅遊資料」：依連假與請假最佳化回傳達最小長度的出遊時段（含建議請假日），不引入任何旅遊資料來源。驗證：單元測試只回傳 tripLength >= minTripLength 的窗口並依 leave efficiency 排序；grep 確認無機票/飯店 API 依賴。
- [x] 2.7 實作 Reject unavailable years and invalid input：年份無資料、日期格式錯誤或 range 顛倒時回傳結構化錯誤，不丟未處理例外。驗證：單元測試對缺資料年份回傳 year_unavailable 含 availableYears，對壞日期回傳 invalid_input。

## 3. MCP server 薄殼

- [x] 3.1 實作 Remote MCP server exposing workday tools，落實「部署於 Cloudflare Workers，使用 agents SDK 的 McpAgent / Streamable HTTP」：以 McpAgent 在固定路徑（/mcp）經 Streamable HTTP 註冊 5 個工具且薄殼不含運算邏輯。驗證：以 MCP Inspector 連線可列出 optimize_leave、count_workdays、add_workdays、next_makeup_workday、find_travel_windows 五個工具。
- [x] 3.2 實作 Tool input and output contracts，落實「首版 4 個工具的輸入輸出契約」：工具邊界日期採 YYYY-MM-DD、轉換為 engine 內部格式，各工具回傳 design 契約定義的形狀。驗證：對每個工具以有效輸入呼叫一次，斷言回傳欄位符合契約（如 count_workdays 回 { workdays, holidays, makeupWorkdays }）。
- [x] 3.3 實作 Structured errors for invalid requests：年份不可用回 { error: "year_unavailable", availableYears }、輸入無效回 { error: "invalid_input", detail }，不使 Worker crash。驗證：對缺資料年份與壞日期各呼叫一次，斷言回傳對應 error 結構且 HTTP 連線未中斷。
- [x] 3.4 確保 Public read-only stateless operation：server 無需認證、無持久狀態、不變更任何資料，且不影響既有公開網站與 jsDelivr JSON API。驗證：無憑證連線即可呼叫工具；檢視程式碼無寫入 KV/R2/資料的路徑；既有網站本地服務行為不變。

## 4. 部署與文件

- [x] 4.1 完成 mcp/wrangler.jsonc 部署設定，使 MCP Worker 可部署且 data/ 隨之 bundle。驗證：`npx wrangler dev` 於 mcp/ 啟動後，MCP Inspector 連上 /mcp 並成功呼叫一個工具取得結果。
- [x] 4.2 更新 README.md 新增 MCP 端點與工具使用說明段落、新增 mcp/README.md 連線指引。驗證：內容審查確認列出 5 個工具的輸入輸出與連線 URL，且既有 API 端點段落維持不變。
