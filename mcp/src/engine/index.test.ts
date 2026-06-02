import { describe, expect, it } from "vitest";
import cal2025Raw from "../../../data/2025.json";
import cal2026Raw from "../../../data/2026.json";
import {
  addWorkdays,
  countWorkdays,
  findTravelWindows,
  isMakeupWorkday,
  isWorkday,
  nextMakeupWorkday,
  optimizeLeave,
} from "./index.js";
import type { Calendar, CalendarDay } from "./types.js";

const cal2025 = cal2025Raw as unknown as Calendar;
const cal2026 = cal2026Raw as unknown as Calendar;
const calendars = { 2025: cal2025, 2026: cal2026 };

function day(cal: Calendar, compact: string): CalendarDay {
  const d = cal.find((x) => x.date === compact);
  if (!d) throw new Error(`fixture missing ${compact}`);
  return d;
}

describe("Workday determination from calendar data", () => {
  it("treats an ordinary weekday as a workday", () => {
    expect(isWorkday(day(cal2025, "20250206"))).toBe(true);
  });
  it("treats a national holiday as a non-working day", () => {
    expect(isWorkday(day(cal2025, "20250101"))).toBe(false); // 開國紀念日
  });
  it("treats a makeup Saturday as a workday", () => {
    const makeup = day(cal2025, "20250208"); // 補行上班
    expect(isMakeupWorkday(makeup)).toBe(true);
    expect(isWorkday(makeup)).toBe(true);
  });
});

describe("Count workdays in a date range", () => {
  it("counts workdays, holidays and makeup days across a range with a makeup workday", () => {
    // 2025-02-06..02-12: 06,07 work; 08 makeup(work); 09 Sun off; 10,11,12 work
    expect(countWorkdays(cal2025, "2025-02-06", "2025-02-12")).toEqual({
      workdays: 6,
      holidays: 1,
      makeupWorkdays: 1,
    });
  });
  it("rejects malformed dates", () => {
    expect(countWorkdays(cal2025, "2025/02/06", "2025-02-12")).toMatchObject({
      error: "invalid_input",
    });
  });
  it("rejects an inverted range", () => {
    expect(countWorkdays(cal2025, "2025-02-12", "2025-02-06")).toMatchObject({
      error: "invalid_input",
    });
  });
});

describe("Add workdays to a date", () => {
  it("adds one workday across an ordinary weekend (Fri -> Mon)", () => {
    expect(addWorkdays(cal2026, "2026-01-02", 1)).toEqual({ date: "2026-01-05" });
  });
  it("counts a makeup Saturday as the next workday", () => {
    expect(addWorkdays(cal2025, "2025-02-07", 1)).toEqual({ date: "2025-02-08" });
  });
  it("walks backward for negative workdays", () => {
    expect(addWorkdays(cal2026, "2026-01-05", -1)).toEqual({ date: "2026-01-02" });
  });
  it("returns the start date for zero workdays", () => {
    expect(addWorkdays(cal2026, "2026-01-05", 0)).toEqual({ date: "2026-01-05" });
  });
  it("rejects a non-integer workday count", () => {
    expect(addWorkdays(cal2026, "2026-01-05", 1.5)).toMatchObject({
      error: "invalid_input",
    });
  });
});

describe("Identify makeup workdays", () => {
  it("finds the next makeup workday on or after a base date", () => {
    expect(nextMakeupWorkday(cal2025, { from: "2025-01-01" })).toEqual({
      next: "2025-02-08",
    });
  });
  it("returns null when no makeup workday follows the base date", () => {
    expect(nextMakeupWorkday(cal2025, { from: "2025-03-01" })).toEqual({
      next: null,
    });
  });
  it("lists all makeup workdays in a range", () => {
    const res = nextMakeupWorkday(cal2025, {
      range: { start: "2025-01-01", end: "2025-12-31" },
    });
    expect(res).toEqual({ next: "2025-02-08", all: ["2025-02-08"] });
  });
  it("requires from or range", () => {
    expect(nextMakeupWorkday(cal2025, {})).toMatchObject({
      error: "invalid_input",
    });
  });
});

describe("Optimize annual leave", () => {
  it("bridges the 2026 Lunar New Year holiday", () => {
    const plans = optimizeLeave(calendars, { year: 2026, annualLeaveDays: 5 });
    expect(Array.isArray(plans)).toBe(true);
    const springFestival = (plans as Exclude<typeof plans, { error: string }>).find(
      (p) => p.offRange.start === "2026-02-07" && p.offRange.end === "2026-02-22",
    );
    expect(springFestival).toBeDefined();
    expect(springFestival).toMatchObject({
      leaveSpent: 5,
      totalDaysOff: 16,
      efficiency: 16 / 5,
    });
    expect(springFestival?.leaveDates).toEqual([
      "2026-02-09",
      "2026-02-10",
      "2026-02-11",
      "2026-02-12",
      "2026-02-13",
    ]);
  });

  it("matches the spec example: 1 leave day bridging a holiday to a weekend yields efficiency 4.0", () => {
    // GIVEN a holiday (Thu) + a normal workday (Fri) + a weekend (Sat, Sun)
    const synthetic: Calendar = [
      { date: "20300103", week: "四", isHoliday: true, description: "假日" },
      { date: "20300104", week: "五", isHoliday: false, description: "" },
      { date: "20300105", week: "六", isHoliday: true, description: "" },
      { date: "20300106", week: "日", isHoliday: true, description: "" },
    ];
    const plans = optimizeLeave({ 2030: synthetic }, {
      year: 2030,
      annualLeaveDays: 1,
    });
    expect(plans).toEqual([
      {
        leaveDates: ["2030-01-04"],
        offRange: { start: "2030-01-03", end: "2030-01-06" },
        totalDaysOff: 4,
        leaveSpent: 1,
        efficiency: 4,
      },
    ]);
  });

  it("returns plans sorted by efficiency descending", () => {
    const plans = optimizeLeave(calendars, {
      year: 2026,
      annualLeaveDays: 5,
    }) as Exclude<ReturnType<typeof optimizeLeave>, { error: string }>;
    for (let i = 1; i < plans.length; i += 1) {
      expect(plans[i - 1].efficiency).toBeGreaterThanOrEqual(plans[i].efficiency);
    }
  });

  it("rejects an unavailable year", () => {
    const res = optimizeLeave(calendars, { year: 1999, annualLeaveDays: 3 });
    expect(res).toMatchObject({ error: "year_unavailable" });
    expect((res as { availableYears: number[] }).availableYears).toEqual([2025, 2026]);
  });

  it("rejects a non-positive leave budget", () => {
    expect(optimizeLeave(calendars, { year: 2026, annualLeaveDays: 0 })).toMatchObject(
      { error: "invalid_input" },
    );
  });
});

describe("Find travel windows", () => {
  it("returns only windows meeting the minimum trip length, sorted by efficiency", () => {
    const windows = findTravelWindows(calendars, {
      year: 2026,
      annualLeaveDays: 5,
      minTripLength: 10,
    }) as Exclude<ReturnType<typeof findTravelWindows>, { error: string }>;
    expect(windows.length).toBeGreaterThan(0);
    for (const w of windows) expect(w.tripLength).toBeGreaterThanOrEqual(10);
    expect(windows.some((w) => w.tripRange.start === "2026-02-07")).toBe(true);
    for (let i = 1; i < windows.length; i += 1) {
      expect(windows[i - 1].tripLength / windows[i - 1].leaveSpent).toBeGreaterThanOrEqual(
        windows[i].tripLength / windows[i].leaveSpent,
      );
    }
  });

  it("returns an empty list when no window reaches the minimum length", () => {
    expect(
      findTravelWindows(calendars, {
        year: 2026,
        annualLeaveDays: 5,
        minTripLength: 999,
      }),
    ).toEqual([]);
  });

  it("rejects an unavailable year", () => {
    expect(
      findTravelWindows(calendars, {
        year: 1999,
        annualLeaveDays: 5,
        minTripLength: 3,
      }),
    ).toMatchObject({ error: "year_unavailable" });
  });
});
