// workday-engine — framework-agnostic pure computations over Taiwan calendar data.
// No I/O, no MCP/HTTP awareness. Callers pass in already-loaded calendar data.
//
// Workday rule (design.md "工作日判定規則"): a day is a workday iff isHoliday===false.
// Weekends and national holidays have isHoliday===true; makeup workdays
// (補班/補行上班/調整上班) have isHoliday===false and therefore count as workdays.

import type {
  AddWorkdaysResult,
  Calendar,
  CalendarDay,
  CountWorkdaysResult,
  DateRange,
  EngineError,
  LeavePlan,
  NextMakeupWorkdayResult,
  TravelWindow,
} from "./types.js";

const MAKEUP_KEYWORDS = ["調整上班", "補行上班", "補班"];
const ISO_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

// ---- date helpers ----

function isValidIso(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const m = ISO_RE.exec(value);
  if (!m) return false;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  const dt = new Date(Date.UTC(y, mo - 1, d));
  return (
    dt.getUTCFullYear() === y &&
    dt.getUTCMonth() === mo - 1 &&
    dt.getUTCDate() === d
  );
}

function isoToCompact(iso: string): string {
  return iso.replace(/-/g, "");
}

function compactToIso(compact: string): string {
  return `${compact.slice(0, 4)}-${compact.slice(4, 6)}-${compact.slice(6, 8)}`;
}

function invalid(detail: string): EngineError {
  return { error: "invalid_input", detail };
}

// ---- day predicates ----

export function isMakeupWorkday(day: CalendarDay): boolean {
  return !day.isHoliday && MAKEUP_KEYWORDS.some((k) => day.description.includes(k));
}

export function isWorkday(day: CalendarDay): boolean {
  return !day.isHoliday;
}

// Defensive ascending sort by compact date; data is already chronological.
function sorted(calendar: Calendar): Calendar {
  return [...calendar].sort((a, b) => a.date.localeCompare(b.date));
}

// ---- count_workdays ----

export function countWorkdays(
  calendar: Calendar,
  start: string,
  end: string,
): CountWorkdaysResult | EngineError {
  if (!isValidIso(start) || !isValidIso(end)) {
    return invalid("dates must be in YYYY-MM-DD form");
  }
  const startC = isoToCompact(start);
  const endC = isoToCompact(end);
  if (startC > endC) return invalid("start must not be after end");

  let workdays = 0;
  let holidays = 0;
  let makeupWorkdays = 0;
  for (const day of calendar) {
    if (day.date < startC || day.date > endC) continue;
    if (day.isHoliday) {
      holidays += 1;
    } else {
      workdays += 1;
      if (isMakeupWorkday(day)) makeupWorkdays += 1;
    }
  }
  return { workdays, holidays, makeupWorkdays };
}

// ---- add_workdays ----

export function addWorkdays(
  calendar: Calendar,
  from: string,
  workdays: number,
): AddWorkdaysResult | EngineError {
  if (!isValidIso(from)) return invalid("from must be in YYYY-MM-DD form");
  if (!Number.isInteger(workdays)) return invalid("workdays must be an integer");

  if (workdays === 0) return { date: from };

  const days = sorted(calendar);
  const fromC = isoToCompact(from);
  const step = workdays > 0 ? 1 : -1;
  const target = Math.abs(workdays);

  // Index of the first day strictly after `from` (forward) — `from` is never counted.
  let idx: number;
  if (step > 0) {
    idx = days.findIndex((d) => d.date > fromC);
    if (idx === -1) return invalid("result is beyond available calendar data");
  } else {
    idx = -1;
    for (let i = days.length - 1; i >= 0; i--) {
      if (days[i].date < fromC) {
        idx = i;
        break;
      }
    }
    if (idx === -1) return invalid("result is beyond available calendar data");
  }

  let counted = 0;
  for (let i = idx; i >= 0 && i < days.length; i += step) {
    if (isWorkday(days[i])) {
      counted += 1;
      if (counted === target) return { date: compactToIso(days[i].date) };
    }
  }
  return invalid("result is beyond available calendar data");
}

// ---- next_makeup_workday ----

export function nextMakeupWorkday(
  calendar: Calendar,
  opts: { from?: string; range?: DateRange },
): NextMakeupWorkdayResult | EngineError {
  const { from, range } = opts;
  const days = sorted(calendar);

  if (range) {
    if (!isValidIso(range.start) || !isValidIso(range.end)) {
      return invalid("range dates must be in YYYY-MM-DD form");
    }
    const s = isoToCompact(range.start);
    const e = isoToCompact(range.end);
    if (s > e) return invalid("range start must not be after end");
    const all = days
      .filter((d) => d.date >= s && d.date <= e && isMakeupWorkday(d))
      .map((d) => compactToIso(d.date));
    return { next: all.length > 0 ? all[0] : null, all };
  }

  if (from !== undefined) {
    if (!isValidIso(from)) return invalid("from must be in YYYY-MM-DD form");
    const fromC = isoToCompact(from);
    const hit = days.find((d) => d.date >= fromC && isMakeupWorkday(d));
    return { next: hit ? compactToIso(hit.date) : null };
  }

  return invalid("either from or range must be provided");
}

// ---- leave optimization (shared by optimize_leave and find_travel_windows) ----

interface OffRun {
  startIdx: number;
  endIdx: number;
}

// Maximal runs of consecutive off-days (isHoliday===true) within a day list.
function offRuns(days: Calendar): OffRun[] {
  const runs: OffRun[] = [];
  let i = 0;
  while (i < days.length) {
    if (days[i].isHoliday) {
      const startIdx = i;
      while (i < days.length && days[i].isHoliday) i += 1;
      runs.push({ startIdx, endIdx: i - 1 });
    } else {
      i += 1;
    }
  }
  return runs;
}

// Select a year's days (optionally clipped to a range), or return an error.
function selectYearDays(
  calendars: Record<number, Calendar>,
  year: number,
  range?: DateRange,
): Calendar | EngineError {
  const cal = calendars[year];
  if (!cal) {
    return {
      error: "year_unavailable",
      availableYears: Object.keys(calendars)
        .map(Number)
        .sort((a, b) => a - b),
    };
  }
  let days = sorted(cal);
  if (range) {
    if (!isValidIso(range.start) || !isValidIso(range.end)) {
      return invalid("range dates must be in YYYY-MM-DD form");
    }
    const s = isoToCompact(range.start);
    const e = isoToCompact(range.end);
    if (s > e) return invalid("range start must not be after end");
    days = days.filter((d) => d.date >= s && d.date <= e);
  }
  return days;
}

// Bridge plans: for each gap of workdays between two adjacent off-runs whose
// length fits the leave budget, taking the whole gap as leave merges the
// surrounding off-runs into one continuous break.
function bridgePlans(days: Calendar, annualLeaveDays: number): LeavePlan[] {
  const runs = offRuns(days);
  const plans: LeavePlan[] = [];
  for (let r = 0; r + 1 < runs.length; r += 1) {
    const left = runs[r];
    const right = runs[r + 1];
    const gapLen = right.startIdx - left.endIdx - 1;
    if (gapLen < 1 || gapLen > annualLeaveDays) continue;

    const leaveDates: string[] = [];
    for (let i = left.endIdx + 1; i < right.startIdx; i += 1) {
      leaveDates.push(compactToIso(days[i].date));
    }
    const offRange: DateRange = {
      start: compactToIso(days[left.startIdx].date),
      end: compactToIso(days[right.endIdx].date),
    };
    const totalDaysOff = right.endIdx - left.startIdx + 1;
    const leaveSpent = gapLen;
    plans.push({
      leaveDates,
      offRange,
      totalDaysOff,
      leaveSpent,
      efficiency: totalDaysOff / leaveSpent,
    });
  }
  plans.sort(
    (a, b) =>
      b.efficiency - a.efficiency ||
      b.totalDaysOff - a.totalDaysOff ||
      a.offRange.start.localeCompare(b.offRange.start),
  );
  return plans;
}

export function optimizeLeave(
  calendars: Record<number, Calendar>,
  params: { year: number; annualLeaveDays: number; range?: DateRange },
): LeavePlan[] | EngineError {
  const { year, annualLeaveDays, range } = params;
  if (!Number.isInteger(annualLeaveDays) || annualLeaveDays < 1) {
    return invalid("annualLeaveDays must be a positive integer");
  }
  const days = selectYearDays(calendars, year, range);
  if ("error" in days) return days;
  return bridgePlans(days, annualLeaveDays);
}

export function findTravelWindows(
  calendars: Record<number, Calendar>,
  params: {
    year: number;
    annualLeaveDays: number;
    minTripLength: number;
    range?: DateRange;
  },
): TravelWindow[] | EngineError {
  const { year, annualLeaveDays, minTripLength, range } = params;
  if (!Number.isInteger(annualLeaveDays) || annualLeaveDays < 1) {
    return invalid("annualLeaveDays must be a positive integer");
  }
  if (!Number.isInteger(minTripLength) || minTripLength < 1) {
    return invalid("minTripLength must be a positive integer");
  }
  const days = selectYearDays(calendars, year, range);
  if ("error" in days) return days;

  return bridgePlans(days, annualLeaveDays)
    .filter((p) => p.totalDaysOff >= minTripLength)
    .map((p) => ({
      tripRange: p.offRange,
      tripLength: p.totalDaysOff,
      leaveDates: p.leaveDates,
      leaveSpent: p.leaveSpent,
    }))
    .sort(
      (a, b) =>
        b.tripLength / b.leaveSpent - a.tripLength / a.leaveSpent ||
        b.tripLength - a.tripLength,
    );
}
