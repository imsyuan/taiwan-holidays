# workday-mcp-server Specification

## Purpose

TBD - created by archiving change 'taiwan-workday-mcp'. Update Purpose after archive.

## Requirements

### Requirement: Remote MCP server exposing workday tools

The system SHALL provide a remote MCP server deployed on Cloudflare Workers that exposes the workday-engine computations as MCP tools over the Streamable HTTP transport at a fixed path. The server SHALL be a thin shell: it SHALL parse tool input, invoke workday-engine, and wrap the result, and it MUST NOT reimplement calculation logic.

#### Scenario: Client lists available tools

- **WHEN** an MCP client connects to the server endpoint
- **THEN** the server advertises the tools `optimize_leave`, `count_workdays`, `add_workdays`, `next_makeup_workday`, and `find_travel_windows`

#### Scenario: Client invokes a tool successfully

- **WHEN** an MCP client calls a registered tool with valid input
- **THEN** the server returns the structured result produced by workday-engine


<!-- @trace
source: taiwan-workday-mcp
updated: 2026-06-02
code:
  - mcp/scripts/gen-manifest.mjs
  - mcp/src/data.ts
  - mcp/README.md
  - mcp/src/engine/types.ts
  - index.html
  - .agents/skills/spectra-discuss/SKILL.md
  - .agents/skills/spectra-apply/SKILL.md
  - mcp/vitest.config.ts
  - mcp/wrangler.jsonc
  - mcp/scripts/verify-mcp.mjs
  - .agents/skills/spectra-commit/SKILL.md
  - .agents/skills/spectra-audit/SKILL.md
  - .agents/skills/spectra-ingest/SKILL.md
  - .spectra.yaml
  - .agents/skills/spectra-drift/SKILL.md
  - mcp/src/engine/index.ts
  - style.css
  - AGENTS.md
  - mcp/src/index.ts
  - mcp/package.json
  - app.js
  - .agents/skills/spectra-propose/SKILL.md
  - mcp/tsconfig.json
  - README.md
  - .agents/skills/spectra-ask/SKILL.md
  - .agents/skills/spectra-archive/SKILL.md
  - .agents/skills/spectra-debug/SKILL.md
  - CLAUDE.md
tests:
  - mcp/src/engine/index.test.ts
-->

---
### Requirement: Tool input and output contracts

The server SHALL accept and return dates as `YYYY-MM-DD` strings at the tool boundary and convert to the engine's internal format internally. Each tool SHALL conform to a defined input and output shape.

#### Scenario: count_workdays returns counts

- **WHEN** `count_workdays` is called with an inclusive `{ start, end }`
- **THEN** the server returns `{ workdays, holidays, makeupWorkdays }`

#### Scenario: add_workdays returns the resulting date

- **WHEN** `add_workdays` is called with `{ from, workdays }`
- **THEN** the server returns `{ date }` for the Nth workday from `from`

#### Scenario: optimize_leave returns ranked plans

- **WHEN** `optimize_leave` is called with `{ year, annualLeaveDays }`
- **THEN** the server returns plans sorted by efficiency, each with `{ leaveDates, offRange, totalDaysOff, leaveSpent, efficiency }`

#### Scenario: next_makeup_workday returns the next or all makeup days

- **WHEN** `next_makeup_workday` is called with a base date or range
- **THEN** the server returns `{ next }`, and `{ all }` additionally when a range is given

#### Scenario: find_travel_windows returns ranked windows

- **WHEN** `find_travel_windows` is called with `{ year, annualLeaveDays, minTripLength }`
- **THEN** the server returns travel windows sorted by leave efficiency, each with `{ tripRange, tripLength, leaveDates, leaveSpent }`


<!-- @trace
source: taiwan-workday-mcp
updated: 2026-06-02
code:
  - mcp/scripts/gen-manifest.mjs
  - mcp/src/data.ts
  - mcp/README.md
  - mcp/src/engine/types.ts
  - index.html
  - .agents/skills/spectra-discuss/SKILL.md
  - .agents/skills/spectra-apply/SKILL.md
  - mcp/vitest.config.ts
  - mcp/wrangler.jsonc
  - mcp/scripts/verify-mcp.mjs
  - .agents/skills/spectra-commit/SKILL.md
  - .agents/skills/spectra-audit/SKILL.md
  - .agents/skills/spectra-ingest/SKILL.md
  - .spectra.yaml
  - .agents/skills/spectra-drift/SKILL.md
  - mcp/src/engine/index.ts
  - style.css
  - AGENTS.md
  - mcp/src/index.ts
  - mcp/package.json
  - app.js
  - .agents/skills/spectra-propose/SKILL.md
  - mcp/tsconfig.json
  - README.md
  - .agents/skills/spectra-ask/SKILL.md
  - .agents/skills/spectra-archive/SKILL.md
  - .agents/skills/spectra-debug/SKILL.md
  - CLAUDE.md
tests:
  - mcp/src/engine/index.test.ts
-->

---
### Requirement: Serve calendar data from bundled assets

The server SHALL read calendar data from `data/<year>.json` bundled with the Worker deployment and MUST NOT fetch this data from jsDelivr or any external CDN at request time. The set of available years SHALL be derived from the bundled data, not from a hardcoded range.

#### Scenario: Tool call resolves data without external fetch

- **WHEN** a tool is invoked for a year whose data is bundled
- **THEN** the server resolves the calendar from bundled assets without making an outbound CDN request


<!-- @trace
source: taiwan-workday-mcp
updated: 2026-06-02
code:
  - mcp/scripts/gen-manifest.mjs
  - mcp/src/data.ts
  - mcp/README.md
  - mcp/src/engine/types.ts
  - index.html
  - .agents/skills/spectra-discuss/SKILL.md
  - .agents/skills/spectra-apply/SKILL.md
  - mcp/vitest.config.ts
  - mcp/wrangler.jsonc
  - mcp/scripts/verify-mcp.mjs
  - .agents/skills/spectra-commit/SKILL.md
  - .agents/skills/spectra-audit/SKILL.md
  - .agents/skills/spectra-ingest/SKILL.md
  - .spectra.yaml
  - .agents/skills/spectra-drift/SKILL.md
  - mcp/src/engine/index.ts
  - style.css
  - AGENTS.md
  - mcp/src/index.ts
  - mcp/package.json
  - app.js
  - .agents/skills/spectra-propose/SKILL.md
  - mcp/tsconfig.json
  - README.md
  - .agents/skills/spectra-ask/SKILL.md
  - .agents/skills/spectra-archive/SKILL.md
  - .agents/skills/spectra-debug/SKILL.md
  - CLAUDE.md
tests:
  - mcp/src/engine/index.test.ts
-->

---
### Requirement: Structured errors for invalid requests

The server SHALL return structured error payloads rather than crashing when a requested year is unavailable or input is invalid.

#### Scenario: Unavailable year

- **WHEN** a tool is invoked for a year with no bundled data
- **THEN** the server returns `{ error: "year_unavailable", availableYears }`

#### Scenario: Invalid input

- **WHEN** a tool receives a malformed date or an inverted range
- **THEN** the server returns `{ error: "invalid_input", detail }`


<!-- @trace
source: taiwan-workday-mcp
updated: 2026-06-02
code:
  - mcp/scripts/gen-manifest.mjs
  - mcp/src/data.ts
  - mcp/README.md
  - mcp/src/engine/types.ts
  - index.html
  - .agents/skills/spectra-discuss/SKILL.md
  - .agents/skills/spectra-apply/SKILL.md
  - mcp/vitest.config.ts
  - mcp/wrangler.jsonc
  - mcp/scripts/verify-mcp.mjs
  - .agents/skills/spectra-commit/SKILL.md
  - .agents/skills/spectra-audit/SKILL.md
  - .agents/skills/spectra-ingest/SKILL.md
  - .spectra.yaml
  - .agents/skills/spectra-drift/SKILL.md
  - mcp/src/engine/index.ts
  - style.css
  - AGENTS.md
  - mcp/src/index.ts
  - mcp/package.json
  - app.js
  - .agents/skills/spectra-propose/SKILL.md
  - mcp/tsconfig.json
  - README.md
  - .agents/skills/spectra-ask/SKILL.md
  - .agents/skills/spectra-archive/SKILL.md
  - .agents/skills/spectra-debug/SKILL.md
  - CLAUDE.md
tests:
  - mcp/src/engine/index.test.ts
-->

---
### Requirement: Public read-only stateless operation

The server SHALL operate without authentication, without persistent state, and without mutating any data in this version. It SHALL NOT alter the existing public website or the existing public JSON API served via jsDelivr.

#### Scenario: No authentication required

- **WHEN** any client connects to the server
- **THEN** the server serves tool requests without requiring credentials and without writing any persistent state

<!-- @trace
source: taiwan-workday-mcp
updated: 2026-06-02
code:
  - mcp/scripts/gen-manifest.mjs
  - mcp/src/data.ts
  - mcp/README.md
  - mcp/src/engine/types.ts
  - index.html
  - .agents/skills/spectra-discuss/SKILL.md
  - .agents/skills/spectra-apply/SKILL.md
  - mcp/vitest.config.ts
  - mcp/wrangler.jsonc
  - mcp/scripts/verify-mcp.mjs
  - .agents/skills/spectra-commit/SKILL.md
  - .agents/skills/spectra-audit/SKILL.md
  - .agents/skills/spectra-ingest/SKILL.md
  - .spectra.yaml
  - .agents/skills/spectra-drift/SKILL.md
  - mcp/src/engine/index.ts
  - style.css
  - AGENTS.md
  - mcp/src/index.ts
  - mcp/package.json
  - app.js
  - .agents/skills/spectra-propose/SKILL.md
  - mcp/tsconfig.json
  - README.md
  - .agents/skills/spectra-ask/SKILL.md
  - .agents/skills/spectra-archive/SKILL.md
  - .agents/skills/spectra-debug/SKILL.md
  - CLAUDE.md
tests:
  - mcp/src/engine/index.test.ts
-->