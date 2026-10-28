# Taiwan Workday MCP Server（台灣工作日計算引擎）

A remote [MCP](https://modelcontextprotocol.io) server that turns the Taiwan
holiday dataset into a **time-decision engine** for LLMs / agents and HR /
enterprise systems. It does not just look up holidays — it computes workdays,
makeup days, optimal leave, and travel windows.

- **Engine** (`src/engine/`) — framework-agnostic pure functions, no I/O. Reusable
  by future iCal / npm / REST surfaces.
- **Server** (`src/index.ts`) — a thin shell on Cloudflare Workers exposing the
  engine as MCP tools over the **Streamable HTTP** transport at `/mcp`.
- **Data** — `data/<year>.json` is bundled into the Worker at build time via
  `scripts/gen-manifest.mjs` (years derived from the files on disk). There is no
  runtime fetch to jsDelivr or any external CDN.

This version is public, read-only, and stateless (no auth, no billing).

## Connect

Production endpoint (no auth required):

```
https://mcp.tw-holidays.gooliya.com/mcp
```

- **Claude.ai (web/desktop)** — Settings → Connectors → Add custom connector → URL above.
- **Claude Code** — `claude mcp add --transport http taiwan-workday https://mcp.tw-holidays.gooliya.com/mcp`
- **MCP Inspector** — `npx @modelcontextprotocol/inspector`, Transport = Streamable HTTP, URL above.
- **Any MCP client/agent** — point it at the URL with the Streamable HTTP transport.

## Tools

All dates are `YYYY-MM-DD` strings.

| Tool | Input | Output |
| --- | --- | --- |
| `count_workdays` | `{ start, end }` (inclusive) | `{ workdays, holidays, makeupWorkdays }` — makeup days count as workdays |
| `add_workdays` | `{ from, workdays }` (negative walks back; `from` not counted) | `{ date }` |
| `next_makeup_workday` | `{ from? }` or `{ range? }` | `{ next }`, plus `{ all }` when a range is given |
| `optimize_leave` | `{ year, annualLeaveDays, range? }` | `LeavePlan[]` sorted by efficiency (days off ÷ leave spent), desc |
| `find_travel_windows` | `{ year, annualLeaveDays, minTripLength, range? }` | `TravelWindow[]` (timing only, no booking data) |
| `build_travel_links` | `{ destination, departDate, returnDate?, destinationName?, origin?, adults?, hotelCheckIn?, hotelCheckOut?, rooms? }` | `{ flights[], hotels[], disclaimer, notes? }` — neutral search-page links only |

`LeavePlan = { leaveDates[], offRange: { start, end }, totalDaysOff, leaveSpent, efficiency }`
`TravelWindow = { tripRange: { start, end }, tripLength, leaveDates[], leaveSpent }`

### `build_travel_links`

Turns a chosen trip (typically a `LeavePlan.offRange` / `TravelWindow.tripRange` from the tools above) into
flight and hotel **search links**. It returns no prices or availability, books nothing, calls no external
API and adds no affiliate parameters; every URL just opens the provider's own search page with the route and
dates prefilled.

| Param | Notes |
| --- | --- |
| `destination` | required, 3-letter IATA city/airport code (`TYO`, `NRT`, `KIX`, `BKK`) |
| `origin` | 3-letter IATA code, default `TPE` |
| `departDate`, `returnDate` | `YYYY-MM-DD`; `returnDate` must be on/after `departDate`; omit it for one-way |
| `adults` | integer 1-9, default 1 |
| `destinationName` | place name for hotel search (`"Tokyo"`, `"東京"`), 1-80 chars. **Optional, but without it no hotel links are returned** (an IATA code cannot be turned into a place name without a lookup table) |
| `hotelCheckIn`, `hotelCheckOut` | default to `departDate` / `returnDate`; check-out must be after check-in. A one-way trip needs an explicit `hotelCheckOut` to get hotel links |
| `rooms` | integer 1-9, default 1 |

Providers (each URL pattern was opened in a real browser and confirmed to prefill the route/destination and
dates; test case 2027-02-11 to 02-14, TPE -> Tokyo, 2 adults):

- Flights: Google Flights, Skyscanner (`skyscanner.com.tw`), Trip.com (`tw.trip.com`)
- Hotels: Booking.com (`zh-tw`), Google Hotels (destination + dates only; party size and rooms are not
  carried, the page defaults to 2 guests, and a `notes` entry says so)
- Not included: Agoda and Trip.com hotels. Their search pages ignore a plain place name and need an internal
  numeric city ID (Agoda redirects to the home page; Trip.com leaves the destination blank), so a link would
  not prefill.

Example (`{ destination: "TYO", destinationName: "Tokyo", departDate: "2027-02-11", returnDate: "2027-02-14", adults: 2 }`):

```json
{
  "flights": [
    { "provider": "Google Flights", "url": "https://www.google.com/travel/flights?q=Flights%20from%20TPE%20to%20TYO%20on%202027-02-11%20through%202027-02-14%202%20passengers&hl=en" },
    { "provider": "Skyscanner", "url": "https://www.skyscanner.com.tw/transport/flights/tpe/tyo/270211/270214/?adultsv2=2&rtn=1" },
    { "provider": "Trip.com", "url": "https://tw.trip.com/flights/showfarefirst?dcity=tpe&acity=tyo&ddate=2027-02-11&rdate=2027-02-14&triptype=rt&class=y&quantity=2" }
  ],
  "hotels": [
    { "provider": "Booking.com", "url": "https://www.booking.com/searchresults.zh-tw.html?ss=Tokyo&checkin=2027-02-11&checkout=2027-02-14&group_adults=2&no_rooms=1&group_children=0" },
    { "provider": "Google Hotels", "url": "https://www.google.com/travel/search?q=Tokyo%20hotels%202027-02-11%20to%202027-02-14" }
  ],
  "disclaimer": "以上連結只會開啟各服務商自己的搜尋頁，本工具不提供任何價格或空房／座位資訊，也不代為訂位或訂房；實際價格、可訂狀態與取消規則請在服務商網站確認。連結僅為搜尋捷徑，不代表推薦。"
}
```

Inputs are validated strictly (IATA = 3 letters, real calendar dates, bounded integers) and every free-text
value is percent-encoded, so nothing can add parameters to a URL. Provider URL formats are not stable
contracts; if one stops prefilling, update or drop it in `src/engine/travel.ts`.

### Errors

Tools return a structured payload instead of throwing:

- Year not bundled → `{ error: "year_unavailable", availableYears: [...] }`
- Malformed date / inverted range / bad argument → `{ error: "invalid_input", detail: "..." }`

## Develop

```bash
npm install
npm run gen        # regenerate src/generated/calendars.ts from ../data/*.json
npm test           # workday-engine unit tests (vitest)
npm run typecheck  # tsc --noEmit
npm run dev        # wrangler dev -> http://localhost:8799
```

`npm run dev` serves:

- `GET /` — JSON info (tool names + available years)
- `POST /mcp` — MCP Streamable HTTP endpoint
- `GET /sse` — MCP SSE endpoint (legacy clients)

Verify a running server end-to-end:

```bash
node scripts/verify-mcp.mjs http://localhost:8799/mcp
```

## Deploy

```bash
npm run deploy     # wrangler deploy (requires Cloudflare auth)
```

The server uses a Durable Object (`MCP_OBJECT` → `WorkdayMCP`) for per-session
MCP state; the binding and `v1` migration are declared in `wrangler.jsonc`.
After the dataset updates, redeploy so the newly bundled year ships with the
Worker.

## Notes / limitations (v1)

- `optimize_leave` enumerates every bridgeable gap, so for a full year it can
  return many low-value plans (e.g. taking a whole work-week off to bridge two
  weekends). Results are sorted by efficiency; consumers can take the top N.
- Single country (Taiwan). Multi-country, auth/billing, and a stdio variant are
  intentionally out of scope for this version.
