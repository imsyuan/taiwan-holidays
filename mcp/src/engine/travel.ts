// travel-links — pure builder of neutral search-page URLs for flights and hotels.
// No I/O, no prices, no availability, NO affiliate parameters. Every URL pattern
// below was opened in a real browser with a 2027 test case (TPE -> Tokyo,
// 2027-02-11..02-14, 2 adults) and confirmed to prefill the search form.
//
// Providers deliberately NOT included (verified to need an internal city ID, so
// plain text/IATA input does not prefill): Agoda, Trip.com hotels.
//
// All dynamic values are either validated against a strict whitelist (IATA codes,
// dates, bounded integers) or percent-encoded, so nothing can inject extra
// parameters or break out of a URL component.

import { isValidIso } from "./index.js";
import type {
  EngineError,
  TravelLink,
  TravelLinksParams,
  TravelLinksResult,
} from "./types.js";

const IATA_RE = /^[A-Za-z]{3}$/;
const MAX_NAME_LENGTH = 80;
// eslint-disable-next-line no-control-regex
const CONTROL_RE = /[\u0000-\u001f\u007f]/;

export const TRAVEL_DISCLAIMER =
  "以上連結只會開啟各服務商自己的搜尋頁，本工具不提供任何價格或空房／座位資訊，也不代為訂位或訂房；實際價格、可訂狀態與取消規則請在服務商網站確認。連結僅為搜尋捷徑，不代表推薦。";

function invalid(detail: string): EngineError {
  return { error: "invalid_input", detail };
}

/** encodeURIComponent plus the RFC 3986 reserved characters it leaves alone. */
function enc(value: string): string {
  return encodeURIComponent(value).replace(
    /[!'()*]/g,
    (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`,
  );
}

/** "2027-02-11" -> "270211" (Skyscanner path format). */
function yymmdd(iso: string): string {
  return iso.slice(2).replace(/-/g, "");
}

function boundedInt(
  value: unknown,
  name: string,
  fallback: number,
): number | EngineError {
  if (value === undefined) return fallback;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1 || value > 9) {
    return invalid(`${name} must be an integer from 1 to 9`);
  }
  return value;
}

function optionalDate(value: unknown, name: string): string | undefined | EngineError {
  if (value === undefined) return undefined;
  if (!isValidIso(value)) return invalid(`${name} must be a valid date in YYYY-MM-DD form`);
  return value;
}

export function buildTravelLinks(
  params: TravelLinksParams,
): TravelLinksResult | EngineError {
  const p = (params ?? {}) as Partial<TravelLinksParams>;

  // ---- IATA codes ----
  const originRaw = p.origin === undefined ? "TPE" : p.origin;
  if (typeof originRaw !== "string" || !IATA_RE.test(originRaw)) {
    return invalid("origin must be a 3-letter IATA code (e.g. TPE)");
  }
  if (typeof p.destination !== "string" || !IATA_RE.test(p.destination)) {
    return invalid("destination must be a 3-letter IATA code (e.g. TYO, NRT, KIX)");
  }
  const origin = originRaw.toUpperCase();
  const destination = p.destination.toUpperCase();
  if (origin === destination) {
    return invalid("origin and destination must be different");
  }

  // ---- flight dates ----
  if (!isValidIso(p.departDate)) {
    return invalid("departDate must be a valid date in YYYY-MM-DD form");
  }
  const departDate = p.departDate;
  const returnDate = optionalDate(p.returnDate, "returnDate");
  if (typeof returnDate === "object") return returnDate;
  if (returnDate !== undefined && returnDate < departDate) {
    return invalid("returnDate must not be before departDate");
  }

  // ---- travellers ----
  const adults = boundedInt(p.adults, "adults", 1);
  if (typeof adults === "object") return adults;
  const rooms = boundedInt(p.rooms, "rooms", 1);
  if (typeof rooms === "object") return rooms;

  // ---- hotel inputs ----
  let name: string | undefined;
  if (p.destinationName !== undefined) {
    if (typeof p.destinationName !== "string") {
      return invalid("destinationName must be a string");
    }
    name = p.destinationName.trim();
    if (name.length === 0 || name.length > MAX_NAME_LENGTH || CONTROL_RE.test(name)) {
      return invalid(
        `destinationName must be 1-${MAX_NAME_LENGTH} characters with no control characters`,
      );
    }
  }
  const explicitIn = optionalDate(p.hotelCheckIn, "hotelCheckIn");
  if (typeof explicitIn === "object") return explicitIn;
  const explicitOut = optionalDate(p.hotelCheckOut, "hotelCheckOut");
  if (typeof explicitOut === "object") return explicitOut;
  const checkIn = explicitIn ?? departDate;
  const checkOut = explicitOut ?? returnDate;
  if (checkOut !== undefined && checkOut <= checkIn) {
    // Explicit dates are the caller's mistake; derived dates (same-day trip) just skip hotels.
    if (explicitIn !== undefined || explicitOut !== undefined) {
      return invalid("hotelCheckOut must be after hotelCheckIn");
    }
  }

  // ---- flights ----
  const o = origin.toLowerCase();
  const d = destination.toLowerCase();
  const roundTrip = returnDate !== undefined;

  const googleQuery =
    `Flights from ${origin} to ${destination} on ${departDate}` +
    (roundTrip ? ` through ${returnDate}` : " one way") +
    (adults > 1 ? ` ${adults} passengers` : "");

  const skyscanner =
    `https://www.skyscanner.com.tw/transport/flights/${o}/${d}/${yymmdd(departDate)}/` +
    (roundTrip ? `${yymmdd(returnDate)}/` : "") +
    `?adultsv2=${adults}&rtn=${roundTrip ? 1 : 0}`;

  const trip =
    `https://tw.trip.com/flights/showfarefirst?dcity=${o}&acity=${d}&ddate=${departDate}` +
    (roundTrip ? `&rdate=${returnDate}` : "") +
    `&triptype=${roundTrip ? "rt" : "ow"}&class=y&quantity=${adults}`;

  const flights: TravelLink[] = [
    // hl=en is required: IATA codes in q= were only parsed reliably with hl=en
    // (4/4 loads); with no hl or hl=zh-TW the form was often left blank.
    { provider: "Google Flights", url: `https://www.google.com/travel/flights?q=${enc(googleQuery)}&hl=en` },
    { provider: "Skyscanner", url: skyscanner },
    { provider: "Trip.com", url: trip },
  ];

  // ---- hotels ----
  const hotels: TravelLink[] = [];
  const notes: string[] = [];
  if (name === undefined) {
    notes.push("未提供 destinationName，因此沒有產生住宿連結。");
  } else if (checkOut === undefined) {
    notes.push("單程行程且未提供 hotelCheckOut，因此沒有產生住宿連結。");
  } else if (checkOut <= checkIn) {
    notes.push("去回程為同一天（沒有住宿晚數），因此沒有產生住宿連結。");
  } else {
    hotels.push({
      provider: "Booking.com",
      url:
        `https://www.booking.com/searchresults.zh-tw.html?ss=${enc(name)}` +
        `&checkin=${checkIn}&checkout=${checkOut}` +
        `&group_adults=${adults}&no_rooms=${rooms}&group_children=0`,
    });
    hotels.push({
      provider: "Google Hotels",
      url: `https://www.google.com/travel/search?q=${enc(`${name} hotels ${checkIn} to ${checkOut}`)}`,
    });
    if (adults !== 2 || rooms !== 1) {
      notes.push("Google Hotels 連結只帶入目的地與日期，人數與房間數請在頁面上自行調整（預設 2 人）。");
    }
  }

  const result: TravelLinksResult = { flights, hotels, disclaimer: TRAVEL_DISCLAIMER };
  if (notes.length > 0) result.notes = notes;
  return result;
}
