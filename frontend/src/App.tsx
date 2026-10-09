import { useCallback, useEffect, useRef, useState } from "react";
import mockReport from "./mockFindings.json";
import DetailDrawer from "./components/DetailDrawer";
import DropZone from "./components/DropZone";
import Report from "./components/Report";
import ThemeToggle from "./components/ThemeToggle";
import TileGrid from "./components/TileGrid";
import type { Finding, MockReport } from "./types";

const REPORT = mockReport as MockReport;
const STEP_MS = 550;

type Phase = "idle" | "running" | "done";

export default function App() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [phase, setPhase] = useState<Phase>("idle");
  const [revealed, setRevealed] = useState(0);
  const [claim, setClaim] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [selected, setSelected] = useState<Finding | null>(null);
  const timers = useRef<number[]>([]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("tessera-theme", theme);
    } catch {
      /* private mode: theme just won't persist */
    }
  }, [theme]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("tessera-theme");
      if (saved === "light" || saved === "dark") setTheme(saved);
    } catch {
      /* ignore */
    }
    return () => {
      timers.current.forEach((t) => window.clearTimeout(t));
    };
  }, []);

  const startAnalysis = useCallback((name: string) => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
    setFileName(name);
    setSelected(null);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setRevealed(REPORT.findings.length);
      setPhase("done");
      return;
    }
    setRevealed(0);
    setPhase("running");
    REPORT.findings.forEach((_, i) => {
      timers.current.push(
        window.setTimeout(() => {
          setRevealed(i + 1);
          if (i === REPORT.findings.length - 1) setPhase("done");
        }, STEP_MS * (i + 1)),
      );
    });
  }, []);

  const visible = REPORT.findings.slice(0, revealed);

  return (
    <div
      className="min-h-screen font-sans"
      style={{ background: "var(--paper)", color: "var(--ink)" }}
    >
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:rounded-lg focus:px-4 focus:py-2"
        style={{ background: "var(--accent)", color: "var(--accent-ink)" }}
      >
        Skip to analysis
      </a>

      <header
        className="border-b"
        style={{ borderColor: "var(--line)", background: "var(--paper-2)" }}
      >
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <div>
            <p className="font-display text-3xl leading-none">Tessera</p>
            <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
              Many small pieces of evidence, one clear picture.
            </p>
          </div>
          <ThemeToggle
            theme={theme}
            onToggle={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          />
        </div>
      </header>

      <main id="main" className="mx-auto max-w-5xl px-4 pb-24 pt-6 sm:px-6">
        <p
          className="rounded-xl border px-4 py-2 text-sm"
          style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
        >
          Prototype on mock data — no real analysis runs yet. Nothing leaves your device.
        </p>

        <div className="mt-4">
          <DropZone
            claim={claim}
            onClaimChange={setClaim}
            onAnalyze={startAnalysis}
            running={phase === "running"}
          />
        </div>

        {(phase !== "idle" || revealed > 0) && (
          <>
            {fileName && (
              <p className="mt-6 font-mono text-sm" style={{ color: "var(--ink-muted)" }}>
                {fileName}
                {claim.trim() !== "" && <> · claim: “{claim.trim()}”</>}
              </p>
            )}
            <TileGrid findings={visible} total={REPORT.findings.length} onSelect={setSelected} />
            {phase === "done" && <Report report={REPORT} />}
          </>
        )}
      </main>

      {selected && <DetailDrawer finding={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
