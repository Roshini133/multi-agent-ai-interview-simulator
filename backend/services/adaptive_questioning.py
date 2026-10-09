"""Adaptive difficulty engine.

Difficulty never depends on one score alone. A *composite signal* combines the latest answer with a
rolling window of earlier answers, and relevance acts as a gate. Deterministic and unit-tested.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

LEVELS = ["EASY", "MEDIUM", "HARD"]
INCREASE_AT = 8.0
REINFORCE_BELOW = 5.0


@dataclass
class Decision:
    difficulty: str
    action: str            # increase | maintain | reinforce
    reason: str
    signal: float

    def to_dict(self) -> dict:
        return asdict(self)


def answer_signal(agent: str, ev: dict) -> float:
    """Collapse an evaluation into one 0-10 signal for adaptation."""
    if agent == "technical":
        return (0.4 * ev.get("technical_accuracy", ev.get("overall", 0)) + 0.15 * ev.get("depth", ev.get("overall", 0))
                + 0.15 * ev.get("concept_understanding", ev.get("overall", 0)) + 0.15 * ev.get("relevance", 0) + 0.15 * ev.get("completeness", 0))
    return 0.6 * ev.get("overall", 0) + 0.2 * ev.get("relevance", 0) + 0.2 * ev.get("completeness", 0)


def decide(current: str, agent: str, latest: dict, previous: list[dict] | None = None, topic_on_resume: bool = False) -> Decision:
    """Choose the next difficulty from the latest evaluation and the history of this agent's answers."""
    current = current if current in LEVELS else "MEDIUM"
    latest_signal = answer_signal(agent, latest)
    prev_signals = [answer_signal(agent, p) for p in (previous or [])[-3:]]
    signal = 0.6 * latest_signal + 0.4 * (sum(prev_signals) / len(prev_signals)) if prev_signals else latest_signal
    relevance = latest.get("relevance", 0)
    idx = LEVELS.index(current)
    reinforce_below = REINFORCE_BELOW - (0.5 if topic_on_resume else 0.0)  # skills claimed on the resume get a fairer probe

    if relevance < 3.5 and latest.get("completeness", 0) >= 5 and latest_signal < 6:  # substantive but off-topic
        return Decision(current, "reinforce", "Answer was substantive but off-topic; staying at the same level.", round(signal, 1))
    if signal >= INCREASE_AT and relevance >= 6:
        new = LEVELS[min(idx + 1, len(LEVELS) - 1)]
        reason = "Strong, relevant answer; increasing difficulty." if new != current else "Strong performance; already at the highest level."
        return Decision(new, "increase" if new != current else "maintain", reason, round(signal, 1))
    if signal < reinforce_below:
        new = LEVELS[max(idx - 1, 0)]
        return Decision(new, "reinforce", "Answer was weak; moving to a simpler concept-reinforcement question.", round(signal, 1))
    return Decision(current, "maintain", "Solid answer; keeping the difficulty level.", round(signal, 1))
