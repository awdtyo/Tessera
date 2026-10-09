import type { Status } from "../types";

/** Status is never color-only: distinct icon + label + color per state. */
export default function StatusIcon({ status }: { status: Status }) {
  const common = "h-5 w-5 shrink-0";
  if (status === "confirmed") {
    return (
      <svg className={common} viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <circle cx="10" cy="10" r="8.5" stroke="currentColor" strokeWidth="1.8" />
        <path
          d="M6.5 10.2l2.4 2.4 4.6-5"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }
  if (status === "suspicious") {
    return (
      <svg className={common} viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path
          d="M10 2.8L17.5 16H2.5L10 2.8z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path d="M10 7.5v3.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="10" cy="13.6" r="1.1" fill="currentColor" />
      </svg>
    );
  }
  return (
    <svg className={common} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="10" cy="10" r="8.5" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M7.8 7.6c.3-1.2 1.2-1.9 2.3-1.9 1.3 0 2.3.9 2.3 2 0 1.5-2.2 1.7-2.2 3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <circle cx="10.1" cy="13.9" r="1.1" fill="currentColor" />
    </svg>
  );
}
