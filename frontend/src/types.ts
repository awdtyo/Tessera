/** Finding / Report types mirroring backend/tessera/core/finding.py + aggregator.py. */

export type Status = "confirmed" | "suspicious" | "cannot_determine";
export type Reliability = "ok" | "degraded" | "unreliable" | "error";

export interface Finding {
  module_id: string;
  module_name: string;
  status: Status;
  confidence_low: number;
  confidence_high: number;
  summary: string;
  reasoning: string;
  reliability: Reliability;
  reliability_note: string;
  has_heatmap: boolean;
  runtime_ms: number;
}

export interface MockReport {
  overall_status: Status;
  summary: string;
  agreed: string[];
  disagreed: string[];
  undetermined: string[];
  findings: Finding[];
}

export const STATUS_LABEL: Record<Status, string> = {
  confirmed: "Supports authenticity",
  suspicious: "Signs consistent with editing",
  cannot_determine: "Could not determine",
};

export const RELIABILITY_LABEL: Record<Reliability, string> = {
  ok: "Reliable signal",
  degraded: "Degraded signal",
  unreliable: "Unreliable signal",
  error: "Check failed",
};
