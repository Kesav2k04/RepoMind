"""Specialist evidence analyzers used by RepoMind's deterministic fallback."""

from . import architecture, history, risk, testing

ANALYZERS = {
    "architecture": architecture.analyze,
    "risk": risk.analyze,
    "testing": testing.analyze,
    "history": history.analyze,
}
