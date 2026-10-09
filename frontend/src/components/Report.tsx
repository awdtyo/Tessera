import type { MockReport } from "../types";
import { STATUS_LABEL } from "../types";
import StatusIcon from "./StatusIcon";
import { statusVars } from "./statusStyle";

function NameList({ ids, label }: { ids: string[]; label: string }) {
  if (ids.length === 0) return null;
  return (
    <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
      {label}: <span className="font-mono">{ids.join(", ")}</span>
    </p>
  );
}

/** Summary band: overall status plus which signals agreed / disagreed. */
export default function Report({ report }: { report: MockReport }) {
  const vars = statusVars(report.overall_status);
  return (
    <section
      aria-labelledby="report-heading"
      className="mt-8 rounded-2xl border p-6"
      style={{ background: vars.bg, borderColor: vars.color }}
    >
      <h2 id="report-heading" className="font-display text-2xl">
        Report
      </h2>
      <p className="mt-3 inline-flex items-center gap-2 text-lg font-semibold" style={{ color: vars.color }}>
        <StatusIcon status={report.overall_status} />
        {STATUS_LABEL[report.overall_status]}
      </p>
      <p className="mt-2 max-w-prose leading-relaxed">{report.summary}</p>
      <div className="mt-3">
        <NameList ids={report.agreed} label="Raised concerns" />
        <NameList ids={report.disagreed} label="Supported authenticity" />
        <NameList ids={report.undetermined} label="Inconclusive" />
      </div>
    </section>
  );
}
