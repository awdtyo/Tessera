import type { Status } from "../types";

/** Central status styling: color var + tinted bg var per state. */
export function statusVars(status: Status): { color: string; bg: string } {
  if (status === "confirmed")
    return { color: "var(--st-confirmed)", bg: "var(--st-confirmed-bg)" };
  if (status === "suspicious")
    return { color: "var(--st-suspicious)", bg: "var(--st-suspicious-bg)" };
  return { color: "var(--st-undet)", bg: "var(--st-undet-bg)" };
}
