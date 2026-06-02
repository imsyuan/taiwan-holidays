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

## Tools

All dates are `YYYY-MM-DD` strings.

| Tool | Input | Output |
| --- | --- | --- |
| `count_workdays` | `{ start, end }` (inclusive) | `{ workdays, holidays, makeupWorkdays }` — makeup days count as workdays |
| `add_workdays` | `{ from, workdays }` (negative walks back; `from` not counted) | `{ date }` |
| `next_makeup_workday` | `{ from? }` or `{ range? }` | `{ next }`, plus `{ all }` when a range is given |
| `optimize_leave` | `{ year, annualLeaveDays, range? }` | `LeavePlan[]` sorted by efficiency (days off ÷ leave spent), desc |
| `find_travel_windows` | `{ year, annualLeaveDays, minTripLength, range? }` | `TravelWindow[]` (timing only, no booking data) |

`LeavePlan = { leaveDates[], offRange: { start, end }, totalDaysOff, leaveSpent, efficiency }`
`TravelWindow = { tripRange: { start, end }, tripLength, leaveDates[], leaveSpent }`

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
