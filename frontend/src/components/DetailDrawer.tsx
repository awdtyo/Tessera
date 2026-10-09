import { useEffect, useId, useRef, useState } from "react";
import type { Finding } from "../types";
import { RELIABILITY_LABEL, STATUS_LABEL } from "../types";
import ConfidenceRange from "./ConfidenceRange";
import StatusIcon from "./StatusIcon";
import { statusVars } from "./statusStyle";

interface Props {
  finding: Finding;
  onClose: () => void;
}

/**
 * Detail drawer for one tile. Heatmap is a clearly-labelled simulated
 * overlay (mock data): opacity slider + before/after swipe.
 */
export default function DetailDrawer({ finding, onClose }: Props) {
  const vars = statusVars(finding.status);
  const closeRef = useRef<HTMLButtonElement>(null);
  const [opacity, setOpacity] = useState(70);
  const [swipe, setSwipe] = useState(50);
  const opacityId = useId();
  const swipeId = useId();

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      // Return focus to the tile that opened the drawer.
      document.getElementById(`tile-${finding.module_id}`)?.focus();
    };
  }, [finding.module_id, onClose]);

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-label={`Details: ${finding.module_name}`}
      className="fixed inset-y-0 right-0 z-50 w-full max-w-md overflow-y-auto border-l p-6 shadow-2xl"
      style={{ background: "var(--paper-2)", borderColor: "var(--line)" }}
    >
      <button
        ref={closeRef}
        type="button"
        onClick={onClose}
        className="rounded-lg border px-3 py-1.5 text-sm font-medium"
        style={{ borderColor: "var(--line)" }}
      >
        ← Back to report (Esc)
      </button>

      <p
        className="mt-5 inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold"
        style={{ color: vars.color, background: vars.bg }}
      >
        <StatusIcon status={finding.status} />
        {STATUS_LABEL[finding.status]}
      </p>
      <h2 className="mt-2 font-display text-3xl">{finding.module_name}</h2>
      <p className="mt-2 leading-relaxed">{finding.reasoning}</p>

      <div className="mt-4 rounded-xl border p-4" style={{ borderColor: "var(--line)" }}>
        <p className="text-sm font-semibold">{RELIABILITY_LABEL[finding.reliability]}</p>
        <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
          {finding.reliability_note}
        </p>
      </div>

      <div className="mt-4">
        <ConfidenceRange finding={finding} />
      </div>
      <p className="mt-2 font-mono text-xs" style={{ color: "var(--ink-muted)" }}>
        {finding.runtime_ms} ms · module {finding.module_id}
      </p>

      {finding.has_heatmap && (
        <div className="mt-6">
          <h3 className="font-display text-xl">Heatmap (simulated — mock data)</h3>

          <div
            className="relative mt-3 h-48 overflow-hidden rounded-xl border"
            style={{ borderColor: "var(--line)" }}
          >
            {/* base "photo": muted gradient placeholder */}
            <div
              aria-hidden="true"
              className="absolute inset-0"
              style={{
                background:
                  "linear-gradient(135deg, #4a4a52 0%, #33333c 45%, #55504a 100%)",
              }}
            />
            {/* overlay clipped by the swipe position */}
            <div
              aria-hidden="true"
              className="absolute inset-0"
              style={{
                clipPath: `inset(0 ${100 - swipe}% 0 0)`,
                opacity: opacity / 100,
                background:
                  "radial-gradient(circle at 72% 68%, rgba(208,138,78,0.95) 0%, rgba(208,138,78,0.45) 28%, transparent 55%), radial-gradient(circle at 30% 30%, rgba(79,174,159,0.5) 0%, transparent 40%)",
              }}
            />
          </div>

          <label htmlFor={opacityId} className="mt-4 block text-sm font-medium">
            Heatmap opacity: {opacity}%
          </label>
          <input
            id={opacityId}
            type="range"
            min={0}
            max={100}
            value={opacity}
            onChange={(e) => setOpacity(Number(e.target.value))}
            className="w-full"
          />

          <label htmlFor={swipeId} className="mt-3 block text-sm font-medium">
            Before / after swipe
          </label>
          <input
            id={swipeId}
            type="range"
            min={0}
            max={100}
            value={swipe}
            onChange={(e) => setSwipe(Number(e.target.value))}
            className="w-full"
            aria-describedby={`${swipeId}-hint`}
          />
          <p id={`${swipeId}-hint`} className="text-xs" style={{ color: "var(--ink-muted)" }}>
            Slide left for the original, right for the heatmap overlay.
          </p>
        </div>
      )}
    </div>
  );
}
