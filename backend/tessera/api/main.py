"""Minimal API stub. Full upload + SSE streaming lands in Phase 1 (P1.6)."""

from fastapi import FastAPI

app = FastAPI(title="Tessera")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe so `main` stays runnable from Phase 0 on."""
    return {"status": "ok"}
