---
name: taiwan-workday
description: >-
  台灣工作日與請假規劃：算工作日、補班日、國定假日、連假，找出請假最划算的方案與出遊時段，
  並把選定的日期轉成機票與住宿的搜尋連結（只提供連結，不含價格、不代訂）。
  當使用者問「台灣 2027 國定假日／連假」「這段期間有幾個工作天」「N 個工作天後是哪天」「下一個補班日」
  「怎麼請假最划算」「請 2 天假可以放幾天」「春節／清明／端午／中秋怎麼排假」「找出遊時段」
  「幫我找這幾天的機票和飯店」時使用。
  Taiwan workdays and leave planning: count working days, makeup workdays (補班), national holidays and
  long weekends; find the most efficient leave plans and travel windows; then turn the chosen dates into
  flight and hotel search links (links only, no prices, no booking). Use for questions like "best way to take
  leave around Taiwan holidays", "Taiwan long weekends 2027", "how many working days between two dates",
  "next makeup workday", "plan a trip around Lunar New Year from Taipei", or "find flights and hotels for
  these dates". Backed by the remote MCP server taiwan-workday (official DGPA calendar via data.gov.tw).
---

# taiwan-workday

Time-decision skill for Taiwan: it uses the `taiwan-workday` remote MCP server to compute workdays, makeup
days, leave plans and travel windows from the official government calendar, then hands the chosen dates to
flight/hotel **search links**. Do not compute Taiwan workdays by hand (weekday arithmetic): makeup days and
flexible holidays have no algorithm; always call the tools.

## 何時使用 / When to use

- 算工作日：區間有幾個工作天、第 N 個工作天是哪天、下一個補班日。
- 請假規劃：「請 N 天特休怎麼排最划算」、「哪段時間最適合出遊」。
- 使用者已經選好行程日期，想直接去搜機票／住宿。
- Not for: prices, availability, booking, visas, weather. This skill only returns timing and links.

## 六個 MCP 工具 / The 6 tools

All dates are `YYYY-MM-DD`. Errors come back as structured JSON, not exceptions.

| Tool | Input | Output |
| --- | --- | --- |
| `count_workdays` | `{ start, end }` (inclusive) | `{ workdays, holidays, makeupWorkdays }` |
| `add_workdays` | `{ from, workdays }` (negative walks back; `from` not counted) | `{ date }` |
| `next_makeup_workday` | `{ from? }` or `{ range? }` | `{ next }`, plus `{ all }` for a range |
| `optimize_leave` | `{ year, annualLeaveDays, range? }` | `LeavePlan[]` sorted by efficiency |
| `find_travel_windows` | `{ year, annualLeaveDays, minTripLength, range? }` | `TravelWindow[]` |
| `build_travel_links` | `{ destination, departDate, returnDate?, destinationName?, origin?, adults?, hotelCheckIn?, hotelCheckOut?, rooms? }` | `{ flights[], hotels[], disclaimer, notes? }` |

`LeavePlan = { leaveDates[], offRange: { start, end }, totalDaysOff, leaveSpent, efficiency }`
`TravelWindow = { tripRange: { start, end }, tripLength, leaveDates[], leaveSpent }`

## 連線 / Connect

Production endpoint (no auth, public, read-only): `https://mcp.tw-holidays.gooliya.com/mcp`

- Claude Code: `claude mcp add --transport http taiwan-workday https://mcp.tw-holidays.gooliya.com/mcp`
- Claude.ai (web/desktop): Settings -> Connectors -> Add custom connector -> paste the URL above.
- MCP Inspector: `npx @modelcontextprotocol/inspector`, Transport = Streamable HTTP, URL above.
- Any other MCP client: Streamable HTTP transport, same URL.

If the tools are not available in the session, tell the user to connect the server first (commands above);
do not fall back to guessing dates.

## 流程 / Workflow: leave plan -> trip links

1. **Pick the plan.** Call `optimize_leave` (user has N leave days, wants the most efficient plan) or
   `find_travel_windows` (user wants a trip of at least M days). Always pass `range` to keep the output
   short; without it `optimize_leave` lists every bridgeable gap in the year.
2. **Let the user choose** one plan. Show `leaveDates` (what to request), the off block
   (`offRange` / `tripRange`), and the efficiency.
3. **Map the plan to trip dates.** The off block is the stretch of days the user does not need to work:
   - `departDate` = `offRange.start` (or `tripRange.start`); `returnDate` = `offRange.end` (or `tripRange.end`).
   - The user may use a shorter sub-range (e.g. fly out the evening before, or land back mid-day on the last
     day); only the dates matter for the links, not flight times.
   - The **user decides the destination, the airport, and the flight times.** Ask if missing. Never pick a
     destination for them unless they ask for suggestions, and then present options, not a decision.
4. **Call `build_travel_links`** with `destination` (3-letter IATA code, e.g. `TYO` = Tokyo any airport,
   `NRT`, `HND`, `KIX`, `BKK`), `destinationName` (a place name for hotel search, e.g. "Tokyo" or "東京";
   without it no hotel links are returned), `departDate`, `returnDate`, `adults`, and `rooms` if needed.
   `origin` defaults to `TPE`. Omit `returnDate` for a one-way flight.
5. **Present the links** as search shortcuts, grouped by flights / hotels, and repeat the `disclaimer`.

Providers returned: flights = Google Flights, Skyscanner (Taiwan site), Trip.com (Taiwan site); hotels =
Booking.com, Google Hotels. Links are neutral (no affiliate codes).

## 注意事項 / Caveats

- **No prices, no availability, no booking.** Links open each provider's own search page with the route and
  dates prefilled. Say so; tell the user to confirm price, baggage and cancellation rules on the provider site.
- **Do not present links as bookings or recommendations.** They are shortcuts; no provider is endorsed.
- **Data range.** Bundled years come from `GET https://mcp.tw-holidays.gooliya.com/` (`availableYears`).
  2027 data exists; years beyond the latest return `{ "error": "year_unavailable", "availableYears": [...] }`.
  Report "no official data yet" instead of estimating.
- `optimize_leave` / `find_travel_windows` work inside a **single year**; they do not join holidays across
  New Year.
- **補班 (makeup workdays) rarely exist now**, but when they do they count as working days. The tools handle
  this; never assume Mon-Fri.
- Google Hotels links carry destination and dates only (party size and rooms are not carried; the page
  defaults to 2 guests). The Google Flights link opens in English by design.
- Source of truth: Directorate-General of Personnel Administration (DGPA, 行政院人事行政總處) calendar,
  published via data.gov.tw dataset 14718. Data is Taiwan local calendar dates (no time zones).

## 範例 / Worked example: 2027 春節

User: "我有 2 天特休，2027 年春節附近怎麼請最划算？想 2 個人去東京。"

1. `optimize_leave` with `{ "year": 2027, "annualLeaveDays": 2, "range": { "start": "2027-02-01", "end": "2027-02-28" } }`:

```json
[{"leaveDates":["2027-02-11","2027-02-12"],"offRange":{"start":"2027-02-04","end":"2027-02-14"},"totalDaysOff":11,"leaveSpent":2,"efficiency":5.5}]
```

   -> Request leave on 2027-02-11 and 2027-02-12 to get an 11-day block, 2027-02-04 to 2027-02-14
   (efficiency 5.5 days off per leave day).

2. User chooses Tokyo and the whole block. `build_travel_links` with
   `{ "destination": "TYO", "destinationName": "Tokyo", "departDate": "2027-02-04", "returnDate": "2027-02-14", "adults": 2 }`
   returns (shortened to the URLs):

```
Google Flights  https://www.google.com/travel/flights?q=Flights%20from%20TPE%20to%20TYO%20on%202027-02-04%20through%202027-02-14%202%20passengers&hl=en
Skyscanner      https://www.skyscanner.com.tw/transport/flights/tpe/tyo/270204/270214/?adultsv2=2&rtn=1
Trip.com        https://tw.trip.com/flights/showfarefirst?dcity=tpe&acity=tyo&ddate=2027-02-04&rdate=2027-02-14&triptype=rt&class=y&quantity=2
Booking.com     https://www.booking.com/searchresults.zh-tw.html?ss=Tokyo&checkin=2027-02-04&checkout=2027-02-14&group_adults=2&no_rooms=1&group_children=0
Google Hotels   https://www.google.com/travel/search?q=Tokyo%20hotels%202027-02-04%20to%202027-02-14
```

3. Reply with the plan, the links grouped as flights / hotels, and the disclaimer: the links only open each
   site's search page; price and availability must be confirmed there.

## 安裝此 skill / Install this skill

Skill source: `skills/taiwan-workday/SKILL.md` in https://github.com/imsyuan/taiwan-holidays.

- With the `skills` CLI (it discovers `skills/<name>/SKILL.md` in a GitHub repo):
  `npx skills add imsyuan/taiwan-holidays --skill taiwan-workday`
- Manually (Claude Code): copy the folder to your personal skills directory:
  `mkdir -p ~/.claude/skills && cp -R skills/taiwan-workday ~/.claude/skills/` (or into a project's
  `.claude/skills/`).

The skill needs the MCP server connected (see "Connect" above); installing the skill alone does not add the tools.
