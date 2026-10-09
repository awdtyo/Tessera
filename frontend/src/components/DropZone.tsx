import { useState } from "react";

interface Props {
  claim: string;
  onClaimChange: (value: string) => void;
  onAnalyze: (fileName: string) => void;
  running: boolean;
}

/** Drop zone with optional claim field. No upload — prototype only. */
export default function DropZone({ claim, onClaimChange, onAnalyze, running }: Props) {
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  return (
    <section
      aria-labelledby="drop-heading"
      className="rounded-2xl border p-6 sm:p-8"
      style={{ background: "var(--paper-2)", borderColor: "var(--line)" }}
    >
      <h2 id="drop-heading" className="font-display text-2xl">
        Drop in a photo or video
      </h2>
      <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
        Files stay on this page in the prototype — nothing is uploaded or analyzed yet.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files[0];
          if (f) setFileName(f.name);
        }}
        className="mt-5 rounded-xl border-2 border-dashed p-8 text-center"
        style={{
          borderColor: dragOver ? "var(--accent)" : "var(--line)",
          background: "var(--paper)",
        }}
      >
        <label htmlFor="file-input" className="cursor-pointer font-medium underline">
          Choose a file
        </label>
        <input
          id="file-input"
          type="file"
          accept="image/*,video/*"
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) setFileName(f.name);
          }}
        />
        <span className="text-sm" style={{ color: "var(--ink-muted)" }}>
          {" "}
          or drag it here
        </span>
        {fileName && (
          <p className="mt-2 font-mono text-sm" aria-live="polite">
            {fileName}
          </p>
        )}
      </div>

      <div className="mt-5">
        <label htmlFor="claim-input" className="block text-sm font-medium">
          What is claimed about it? <span style={{ color: "var(--ink-muted)" }}>(optional)</span>
        </label>
        <textarea
          id="claim-input"
          value={claim}
          onChange={(e) => onClaimChange(e.target.value)}
          rows={2}
          placeholder='e.g. "this is from today&apos;s flood"'
          className="mt-1 w-full rounded-xl border p-3 text-sm"
          style={{
            background: "var(--paper)",
            borderColor: "var(--line)",
            color: "var(--ink)",
          }}
        />
      </div>

      <button
        type="button"
        disabled={running}
        onClick={() => onAnalyze(fileName ?? "demo-sample.jpg")}
        className="mt-5 rounded-xl px-6 py-3 font-semibold disabled:opacity-50"
        style={{ background: "var(--accent)", color: "var(--accent-ink)" }}
      >
        {running ? "Analyzing…" : "Analyze (mock)"}
      </button>
    </section>
  );
}
