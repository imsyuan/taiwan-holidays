// Data access layer for the MCP server.
//
// Calendar data is read from CALENDARS, which is generated at build time by
// scripts/gen-manifest.mjs from the repo's data/<year>.json files and bundled
// into the Worker. There is NO runtime fetch to jsDelivr or any external CDN.
// The set of available years is derived from the bundled data, not from a
// hardcoded numeric range.

import { CALENDARS } from "./generated/calendars.js";
import type { Calendar } from "./engine/types.js";

/** Years present in the bundled data, ascending. */
export const availableYears: number[] = Object.keys(CALENDARS)
  .map(Number)
  .sort((a, b) => a - b);

/** Year -> calendar map, consumed by year-based engine functions. */
export const calendarsByYear: Record<number, Calendar> = CALENDARS;

/**
 * All bundled days concatenated and sorted by date. Date-range / walking
 * engine functions (count_workdays, add_workdays, next_makeup_workday) operate
 * over this flat multi-year calendar so they can span year boundaries.
 */
export const allDays: Calendar = availableYears
  .flatMap((y) => CALENDARS[y])
  .sort((a, b) => a.date.localeCompare(b.date));
