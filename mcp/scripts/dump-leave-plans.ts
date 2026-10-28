// Dumps golden leave plans from the TypeScript workday-engine so the Python
// port in scripts/generate_pages.py can be checked for exact parity.
//
// Regenerate the golden file (run from the repo root):
//
//   cd mcp && npx --yes tsx@4 scripts/dump-leave-plans.ts && cd ..
//
// Then verify the Python port still matches:
//
//   python3 scripts/test_generate_pages.py
//
// Output: scripts/golden/leave_plans.json, keyed by year, then by
// annualLeaveDays budget, holding the exact optimizeLeave() result arrays.
// Years and budgets are fixed so the golden file is stable; pass years as CLI
// arguments to override (e.g. `tsx scripts/dump-leave-plans.ts 2026 2027`).

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { optimizeLeave } from "../src/engine/index.js";
import type { Calendar, LeavePlan } from "../src/engine/types.js";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..");
const outFile = join(repoRoot, "scripts", "golden", "leave_plans.json");

const DEFAULT_YEARS = [2026, 2027];
const BUDGETS = [1, 2, 3, 4, 5];

const years =
  process.argv.length > 2 ? process.argv.slice(2).map(Number) : DEFAULT_YEARS;

const calendars: Record<number, Calendar> = {};
for (const y of years) {
  const raw = readFileSync(join(repoRoot, "data", `${y}.json`), "utf-8");
  calendars[y] = JSON.parse(raw) as Calendar;
}

const golden: Record<string, Record<string, LeavePlan[]>> = {};
for (const y of years) {
  golden[String(y)] = {};
  for (const budget of BUDGETS) {
    const plans = optimizeLeave(calendars, { year: y, annualLeaveDays: budget });
    if (!Array.isArray(plans)) {
      throw new Error(`optimizeLeave(${y}, ${budget}) failed: ${JSON.stringify(plans)}`);
    }
    golden[String(y)][String(budget)] = plans;
  }
}

mkdirSync(dirname(outFile), { recursive: true });
writeFileSync(outFile, JSON.stringify(golden, null, 2) + "\n");
console.log(
  `Wrote ${outFile} (years: ${years.join(", ")}; budgets: ${BUDGETS.join(", ")})`,
);
