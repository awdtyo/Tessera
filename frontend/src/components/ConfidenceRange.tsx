import type { Finding } from "../types";

/** Confidence is a range bar, never a single number. */
export default function ConfidenceRange({ finding }: { finding: Finding }) {
  const lo = Math.round(finding.confidence_low * 100);
  const hi = Math.round(finding.confidence_high * 100);
  return (
    <div>
      <div
        role="img"
        aria-label={`Confidence between ${lo} and ${hi} percent`}
        style={{ background: "var(--line)" }}
        className="relative h-2 w-full rounded-full"
      >
        <div
          aria-hidden="true"
          className="absolute top-0 h-2 rounded-full"
          style={{
            left: `${finding.confidence_low * 100}%`,
            width: `${(finding.confidence_high - finding.confidence_low) * 100}%`,
            background: "var(--accent)",
          }}
        />
      </div>
      <p className="mt-1 font-mono text-xs" style={{ color: "var(--ink-muted)" }}>
        {lo}–{hi}%
      </p>
    </div>
  );
}
