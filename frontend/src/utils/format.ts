import i18n from "@/i18n/config";

import { getCompanyTimezone } from "./timezone";

/** uz/ru render numeric dates as DD.MM(.YYYY) - a well-established ICU pattern
 * for "ru-RU" that both languages share for this style. en keeps its existing
 * "15 Aug" / "Aug 15, 2026" wording. Read fresh on each call rather than cached,
 * since this itself isn't a hook - correctness relies on the calling component
 * already re-rendering on language change via its own useTranslation() call. */
function dateLocale(): string {
  return i18n.language === "en" ? "en-GB" : "ru-RU";
}

/** Formats a UTC ISO datetime as "HH:MM" in the company's configured timezone. */
export function formatTime(isoString: string | null | undefined): string {
  if (!isoString) return "-";
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: getCompanyTimezone(),
  }).format(new Date(isoString));
}

/** Formats a plain "YYYY-MM-DD" calendar date (no time/timezone component - the value
 * as stored). Parsed as local calendar fields, not as a UTC instant, so it never
 * shifts by a day depending on the viewer's own timezone. */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "-";
  const [year, month, day] = dateString.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  const locale = dateLocale();
  const options: Intl.DateTimeFormatOptions =
    locale === "en-GB" ? { day: "2-digit", month: "short", year: "numeric" } : { day: "2-digit", month: "2-digit", year: "numeric" };
  return new Intl.DateTimeFormat(locale, options).format(date);
}

export function formatDateShort(dateString: string | null | undefined): string {
  if (!dateString) return "-";
  const [year, month, day] = dateString.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  const locale = dateLocale();
  const options: Intl.DateTimeFormatOptions = locale === "en-GB" ? { day: "2-digit", month: "short" } : { day: "2-digit", month: "2-digit" };
  return new Intl.DateTimeFormat(locale, options).format(date);
}

/** Adds `days` to a plain "YYYY-MM-DD" date, returning the same plain format.
 * Parsed/constructed as local calendar fields throughout, for the same
 * timezone-shift-safety reason as formatDate above. */
export function addDays(dateString: string, days: number): string {
  const [year, month, day] = dateString.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  date.setDate(date.getDate() + days);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return "-";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: getCompanyTimezone(),
  }).format(new Date(isoString));
}

export function formatMinutes(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) return "-";
  if (minutes === 0) return "0 min";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours === 0) return `${mins} min`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}m`;
}

/** "HH:MM:SS" (a Time column) -> "HH:MM". */
export function formatWorkTime(timeString: string | null | undefined): string {
  if (!timeString) return "-";
  return timeString.slice(0, 5);
}

const WEEKDAY_NAMES = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function weekdayName(isoWeekday: number): string {
  return WEEKDAY_NAMES[isoWeekday] ?? "?";
}
