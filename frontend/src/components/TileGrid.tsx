import type { Finding } from "../types";
import Tile from "./Tile";

interface Props {
  findings: Finding[];
  total: number;
  onSelect: (finding: Finding) => void;
}

/** Live-analysis grid that fills as (mock) findings stream in. */
export default function TileGrid({ findings, total, onSelect }: Props) {
  if (findings.length === 0) return null;
  return (
    <section aria-labelledby="tiles-heading" aria-live="polite" className="mt-8">
      <h2 id="tiles-heading" className="font-display text-2xl">
        Checks{" "}
        <span className="font-mono text-base" style={{ color: "var(--ink-muted)" }}>
          {findings.length} of {total}
        </span>
      </h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {findings.map((f) => (
          <Tile key={f.module_id} finding={f} onSelect={onSelect} />
        ))}
      </div>
    </section>
  );
}
