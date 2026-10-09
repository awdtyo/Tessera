interface Props {
  theme: "dark" | "light";
  onToggle: () => void;
}

export default function ThemeToggle({ theme, onToggle }: Props) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={theme === "light"}
      className="rounded-xl border px-4 py-2 text-sm font-medium"
      style={{ borderColor: "var(--line)", background: "var(--paper-2)" }}
    >
      {theme === "dark" ? "☾ Dark · switch to light" : "☀ Light · switch to dark"}
    </button>
  );
}
