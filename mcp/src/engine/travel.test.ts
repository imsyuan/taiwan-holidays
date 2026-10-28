import { describe, expect, it } from "vitest";
import { TRAVEL_DISCLAIMER, buildTravelLinks } from "./travel.js";
import type { TravelLinksResult } from "./types.js";

// The verified 2027 case: TPE -> Tokyo, 2027-02-11..02-14, 2 adults.
const base = {
  destination: "TYO",
  destinationName: "Tokyo",
  departDate: "2027-02-11",
  returnDate: "2027-02-14",
  adults: 2,
};

function ok(params: Parameters<typeof buildTravelLinks>[0]): TravelLinksResult {
  const r = buildTravelLinks(params);
  if ("error" in r) throw new Error(`unexpected error: ${JSON.stringify(r)}`);
  return r;
}

function url(links: { provider: string; url: string }[], provider: string): string {
  const link = links.find((l) => l.provider === provider);
  if (!link) throw new Error(`missing provider ${provider}`);
  return link.url;
}

describe("buildTravelLinks - round trip", () => {
  const r = ok(base);

  it("returns three flight providers and two hotel providers", () => {
    expect(r.flights.map((l) => l.provider)).toEqual(["Google Flights", "Skyscanner", "Trip.com"]);
    expect(r.hotels.map((l) => l.provider)).toEqual(["Booking.com", "Google Hotels"]);
  });

  it("builds the Google Flights natural-language query", () => {
    expect(url(r.flights, "Google Flights")).toBe(
      "https://www.google.com/travel/flights?q=Flights%20from%20TPE%20to%20TYO%20on%202027-02-11%20through%202027-02-14%202%20passengers&hl=en",
    );
  });

  it("builds the Skyscanner Taiwan path with YYMMDD dates", () => {
    expect(url(r.flights, "Skyscanner")).toBe(
      "https://www.skyscanner.com.tw/transport/flights/tpe/tyo/270211/270214/?adultsv2=2&rtn=1",
    );
  });

  it("builds the Trip.com Taiwan flight search", () => {
    expect(url(r.flights, "Trip.com")).toBe(
      "https://tw.trip.com/flights/showfarefirst?dcity=tpe&acity=tyo&ddate=2027-02-11&rdate=2027-02-14&triptype=rt&class=y&quantity=2",
    );
  });

  it("builds the Booking.com search with dates and guests", () => {
    expect(url(r.hotels, "Booking.com")).toBe(
      "https://www.booking.com/searchresults.zh-tw.html?ss=Tokyo&checkin=2027-02-11&checkout=2027-02-14&group_adults=2&no_rooms=1&group_children=0",
    );
  });

  it("builds the Google Hotels search with destination and dates", () => {
    expect(url(r.hotels, "Google Hotels")).toBe(
      "https://www.google.com/travel/search?q=Tokyo%20hotels%202027-02-11%20to%202027-02-14",
    );
  });

  it("carries the Traditional Chinese disclaimer and no notes when nothing was skipped", () => {
    expect(r.disclaimer).toBe(TRAVEL_DISCLAIMER);
    expect(r.disclaimer).toContain("價格");
    expect(r.notes).toBeUndefined();
  });

  it("never adds affiliate or tracking parameters", () => {
    for (const l of [...r.flights, ...r.hotels]) {
      expect(l.url).not.toMatch(/aid=|affid|affiliate|marketing|utm_|allianceid|sid=|cid=|ref=/i);
    }
  });
});

describe("buildTravelLinks - defaults", () => {
  it("defaults origin to TPE, adults to 1, rooms to 1 and hotel dates to the flight dates", () => {
    const r = ok({
      destination: "kix",
      destinationName: "Osaka",
      departDate: "2027-02-11",
      returnDate: "2027-02-14",
    });
    expect(url(r.flights, "Google Flights")).toBe(
      "https://www.google.com/travel/flights?q=Flights%20from%20TPE%20to%20KIX%20on%202027-02-11%20through%202027-02-14&hl=en",
    );
    expect(url(r.flights, "Skyscanner")).toContain("/tpe/kix/270211/270214/?adultsv2=1&rtn=1");
    expect(url(r.flights, "Trip.com")).toContain("quantity=1");
    expect(url(r.hotels, "Booking.com")).toContain(
      "checkin=2027-02-11&checkout=2027-02-14&group_adults=1&no_rooms=1",
    );
  });

  it("honours explicit hotel dates and rooms", () => {
    const r = ok({ ...base, hotelCheckIn: "2027-02-12", hotelCheckOut: "2027-02-13", rooms: 2 });
    expect(url(r.hotels, "Booking.com")).toContain(
      "checkin=2027-02-12&checkout=2027-02-13&group_adults=2&no_rooms=2",
    );
    expect(url(r.hotels, "Google Hotels")).toContain("2027-02-12%20to%202027-02-13");
  });

  it("notes that Google Hotels ignores party size when it differs from the default", () => {
    expect(ok({ ...base, adults: 3 }).notes?.[0]).toContain("Google Hotels");
    expect(ok({ ...base, adults: 2 }).notes).toBeUndefined();
  });
});

describe("buildTravelLinks - one way", () => {
  const r = ok({ destination: "NRT", departDate: "2027-02-11", adults: 2 });

  it("builds one-way flight links without a return date", () => {
    expect(url(r.flights, "Google Flights")).toBe(
      "https://www.google.com/travel/flights?q=Flights%20from%20TPE%20to%20NRT%20on%202027-02-11%20one%20way%202%20passengers&hl=en",
    );
    expect(url(r.flights, "Skyscanner")).toBe(
      "https://www.skyscanner.com.tw/transport/flights/tpe/nrt/270211/?adultsv2=2&rtn=0",
    );
    expect(url(r.flights, "Trip.com")).toBe(
      "https://tw.trip.com/flights/showfarefirst?dcity=tpe&acity=nrt&ddate=2027-02-11&triptype=ow&class=y&quantity=2",
    );
  });

  it("omits hotels and says why", () => {
    expect(r.hotels).toEqual([]);
    expect(r.notes?.join(" ")).toContain("destinationName");
  });

  it("still builds hotels for a one-way trip when check-out is given explicitly", () => {
    const withHotel = ok({
      destination: "NRT",
      destinationName: "Tokyo",
      departDate: "2027-02-11",
      hotelCheckOut: "2027-02-13",
    });
    expect(url(withHotel.hotels, "Booking.com")).toContain("checkin=2027-02-11&checkout=2027-02-13");
  });

  it("explains the missing check-out for a one-way trip with a destination name", () => {
    const r2 = ok({ destination: "NRT", destinationName: "Tokyo", departDate: "2027-02-11" });
    expect(r2.hotels).toEqual([]);
    expect(r2.notes?.join(" ")).toContain("hotelCheckOut");
  });
});

describe("buildTravelLinks - hotels omitted without a destination name", () => {
  it("returns flights only and a note", () => {
    const r = ok({ destination: "TYO", departDate: "2027-02-11", returnDate: "2027-02-14" });
    expect(r.flights).toHaveLength(3);
    expect(r.hotels).toEqual([]);
    expect(r.notes?.[0]).toContain("destinationName");
  });

  it("skips hotels (not an error) for a same-day round trip", () => {
    const r = ok({ ...base, returnDate: "2027-02-11" });
    expect(r.flights).toHaveLength(3);
    expect(r.hotels).toEqual([]);
  });
});

describe("buildTravelLinks - validation", () => {
  const bad = (params: Record<string, unknown>) =>
    buildTravelLinks({ ...base, ...params } as Parameters<typeof buildTravelLinks>[0]);

  it("rejects an impossible calendar date", () => {
    expect(bad({ departDate: "2027-02-30" })).toMatchObject({ error: "invalid_input" });
  });
  it("rejects a malformed date", () => {
    expect(bad({ departDate: "2027/02/11" })).toMatchObject({ error: "invalid_input" });
    expect(bad({ returnDate: "20270214" })).toMatchObject({ error: "invalid_input" });
    expect(bad({ hotelCheckIn: "tomorrow" })).toMatchObject({ error: "invalid_input" });
  });
  it("rejects a return date before the departure date", () => {
    const r = bad({ returnDate: "2027-02-10" });
    expect(r).toMatchObject({ error: "invalid_input" });
    expect((r as { detail: string }).detail).toContain("returnDate");
  });
  it("rejects bad IATA codes", () => {
    expect(bad({ destination: "TOKYO" })).toMatchObject({ error: "invalid_input" });
    expect(bad({ destination: "T1O" })).toMatchObject({ error: "invalid_input" });
    expect(bad({ destination: "" })).toMatchObject({ error: "invalid_input" });
    expect(bad({ destination: "TY&" })).toMatchObject({ error: "invalid_input" });
    expect(bad({ origin: "TW" })).toMatchObject({ error: "invalid_input" });
    expect(bad({ destination: undefined })).toMatchObject({ error: "invalid_input" });
  });
  it("rejects identical origin and destination", () => {
    expect(bad({ destination: "tpe" })).toMatchObject({ error: "invalid_input" });
  });
  it("rejects adults and rooms out of range or non-integer", () => {
    expect(bad({ adults: 0 })).toMatchObject({ error: "invalid_input" });
    expect(bad({ adults: 10 })).toMatchObject({ error: "invalid_input" });
    expect(bad({ adults: 1.5 })).toMatchObject({ error: "invalid_input" });
    expect(bad({ adults: "2" })).toMatchObject({ error: "invalid_input" });
    expect(bad({ rooms: 0 })).toMatchObject({ error: "invalid_input" });
    expect(bad({ rooms: 10 })).toMatchObject({ error: "invalid_input" });
  });
  it("rejects explicit hotel check-out that is not after check-in", () => {
    expect(bad({ hotelCheckIn: "2027-02-12", hotelCheckOut: "2027-02-12" })).toMatchObject({
      error: "invalid_input",
    });
    expect(bad({ hotelCheckOut: "2027-02-10" })).toMatchObject({ error: "invalid_input" });
  });
  it("rejects empty, over-long or control-character destination names", () => {
    expect(bad({ destinationName: "   " })).toMatchObject({ error: "invalid_input" });
    expect(bad({ destinationName: "x".repeat(81) })).toMatchObject({ error: "invalid_input" });
    expect(bad({ destinationName: "Tokyo\nHost: evil" })).toMatchObject({ error: "invalid_input" });
  });
});

describe("buildTravelLinks - URL encoding", () => {
  it("percent-encodes Chinese destination names", () => {
    const r = ok({ ...base, destinationName: "東京" });
    expect(url(r.hotels, "Booking.com")).toContain("ss=%E6%9D%B1%E4%BA%AC&");
    expect(url(r.hotels, "Google Hotels")).toContain("q=%E6%9D%B1%E4%BA%AC%20hotels%20");
  });

  it("cannot be used to inject extra parameters or markup", () => {
    const evil = `Tokyo&aid=123#frag?x=<script>"'()*`;
    const r = ok({ ...base, destinationName: evil });
    for (const l of r.hotels) {
      const parsed = new URL(l.url);
      expect(parsed.hash).toBe("");
      expect(l.url).not.toMatch(/[<>"'#]|&aid=/);
      expect(l.url).not.toContain("*");
    }
    const booking = new URL(url(r.hotels, "Booking.com"));
    expect([...booking.searchParams.keys()]).toEqual([
      "ss",
      "checkin",
      "checkout",
      "group_adults",
      "no_rooms",
      "group_children",
    ]);
    expect(booking.searchParams.get("ss")).toBe(evil);
  });

  it("trims whitespace around the destination name", () => {
    const r = ok({ ...base, destinationName: "  Tokyo  " });
    expect(url(r.hotels, "Booking.com")).toContain("ss=Tokyo&");
  });

  it("normalises IATA case and keeps hosts fixed", () => {
    const r = ok({ ...base, origin: "tpe", destination: "tyo" });
    for (const l of [...r.flights, ...r.hotels]) {
      expect(["www.google.com", "www.skyscanner.com.tw", "tw.trip.com", "www.booking.com"]).toContain(
        new URL(l.url).host,
      );
    }
    expect(url(r.flights, "Google Flights")).toContain("from%20TPE%20to%20TYO");
  });
});
