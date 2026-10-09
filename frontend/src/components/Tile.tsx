import { motion, useReducedMotion } from "framer-motion";
import type { Finding } from "../types";
import { RELIABILITY_LABEL, STATUS_LABEL } from "../types";
import ConfidenceRange from "./ConfidenceRange";
import StatusIcon from "./StatusIcon";
import { statusVars } from "./statusStyle";

interface Props {
  finding: Finding;
  onSelect: (finding: Finding) => void;
}

/** One mosaic tile: status icon + label + color, range bar, reliability badge. */
export default function Tile({ finding, onSelect }: Props) {
  const vars = statusVars(finding.status);
  const reduceMotion = useReducedMotion();
  const showBadge = finding.reliability !== "ok";

  return (
    <motion.button
      type="button"
      id={`tile-${finding.module_id}`}
      onClick={() => onSelect(finding)}
      initial={reduceMotion === true ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduceMotion === true ? 0 : 0.45 }}
      className="w-full rounded-2xl border p-5 text-left"
      style={{
        background: "var(--paper-3)",
        borderColor: "var(--line)",
      }}
      aria-describedby={`tile-${finding.module_id}-summary`}
    >
      <span
        className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold"
        style={{ color: vars.color, background: vars.bg }}
      >
        <StatusIcon status={finding.status} />
        {STATUS_LABEL[finding.status]}
      </span>

      <span className="mt-3 block font-display text-xl leading-snug">{finding.module_name}</span>
      <span
        id={`tile-${finding.module_id}-summary`}
        className="mt-1 block text-sm leading-relaxed"
        style={{ color: "var(--ink-muted)" }}
      >
        {finding.summary}
      </span>

      {showBadge && (
        <span
          className="mt-3 inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium"
          style={{ borderColor: vars.color, color: vars.color }}
        >
          {RELIABILITY_LABEL[finding.reliability]}
        </span>
      )}

      <span className="mt-4 block">
        <ConfidenceRange finding={finding} />
      </span>
      <span
        className="mt-2 block font-mono text-xs"
        style={{ color: "var(--ink-muted)" }}
      >
        {finding.runtime_ms} ms · open details →
      </span>
    </motion.button>
  );
}
