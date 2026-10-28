// Data shapes for the workday-engine. These mirror the on-disk
// data/<year>.json format produced by scripts/update_calendar.py.
// The engine is framework-agnostic and performs no I/O: callers pass in
// already-loaded calendar data.

export interface LunarInfo {
  date: string;
  festivals: string[];
  solarTerm: string | null;
}

export interface CalendarDay {
  /** "YYYYMMDD" */
  date: string;
  /** Chinese weekday character, e.g. "三" */
  week: string;
  /** true = day off (weekends + national holidays); false = workday (incl. makeup) */
  isHoliday: boolean;
  /** Holiday name, makeup marker (補班/補行上班/調整上班), or "" */
  description: string;
  lunar?: LunarInfo | null;
}

export type Calendar = CalendarDay[];

/** Inclusive date range, dates in "YYYY-MM-DD" form. */
export interface DateRange {
  start: string;
  end: string;
}

export interface EngineError {
  error: "year_unavailable" | "invalid_input";
  /** present when error === "year_unavailable" */
  availableYears?: number[];
  /** present when error === "invalid_input" */
  detail?: string;
}

export function isEngineError(value: unknown): value is EngineError {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    ((value as EngineError).error === "year_unavailable" ||
      (value as EngineError).error === "invalid_input")
  );
}

// ---- Result shapes (mirror design.md Implementation Contract) ----

export interface CountWorkdaysResult {
  workdays: number;
  holidays: number;
  makeupWorkdays: number;
}

export interface AddWorkdaysResult {
  /** "YYYY-MM-DD" */
  date: string;
}

export interface NextMakeupWorkdayResult {
  /** "YYYY-MM-DD" or null when none found in loaded data */
  next: string | null;
  /** present only when a range was supplied; all makeup days in range, ascending */
  all?: string[];
}

export interface LeavePlan {
  /** dates to request as leave, "YYYY-MM-DD", ascending */
  leaveDates: string[];
  /** resulting continuous off block */
  offRange: DateRange;
  totalDaysOff: number;
  leaveSpent: number;
  /** totalDaysOff / leaveSpent */
  efficiency: number;
}

export interface TravelWindow {
  tripRange: DateRange;
  tripLength: number;
  leaveDates: string[];
  leaveSpent: number;
}

// ---- Travel links (link-only: no prices, no availability, no affiliate codes) ----

export interface TravelLinksParams {
  /** IATA airport/city code, 3 letters. Default "TPE". */
  origin?: string;
  /** IATA airport/city code, 3 letters. Required. */
  destination: string;
  /** Free-text place name for hotel search (e.g. "Tokyo", "東京"). Optional; hotels are omitted without it. */
  destinationName?: string;
  /** "YYYY-MM-DD" */
  departDate: string;
  /** "YYYY-MM-DD", must be >= departDate. Omit for one-way. */
  returnDate?: string;
  /** 1-9, default 1 */
  adults?: number;
  /** "YYYY-MM-DD", defaults to departDate */
  hotelCheckIn?: string;
  /** "YYYY-MM-DD", defaults to returnDate; must be after the check-in date */
  hotelCheckOut?: string;
  /** 1-9, default 1 */
  rooms?: number;
}

export interface TravelLink {
  provider: string;
  url: string;
}

export interface TravelLinksResult {
  flights: TravelLink[];
  hotels: TravelLink[];
  /** Traditional Chinese: links only, no prices or availability; confirm on the provider site. */
  disclaimer: string;
  /** Present only when something was skipped or not carried into a link (e.g. no hotels). */
  notes?: string[];
}
