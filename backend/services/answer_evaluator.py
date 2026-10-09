"""Answer evaluation = deterministic heuristics + LLM rubric scoring, blended and sanity-capped.

Design goals (see docs/research_notes.md):
* LLM output is validated and clamped; malformed output falls back to heuristics.
* Heuristic-only evaluations are flagged (method="heuristic") and cannot award top scores for
  technical accuracy because correctness cannot be verified without a model.
* Scores are capped for very short answers so the LLM cannot reward non-answers.
"""
from __future__ import annotations

import logging
import re

from prompts.eval_prompts import EVAL_SYSTEM, EXTRA_KEYS, build_eval_prompt
from services.embedding_service import EmbeddingService
from services.ollama_service import LLMError, OllamaService
from services.voice_service import count_fillers
from utils.logging_config import log_event
from utils.roles import ROLES, role_label

log = logging.getLogger(__name__)

COMMON = ["communication", "clarity", "confidence", "completeness", "relevance"]
LLM_WEIGHT = 0.7
EXPECTED_WORDS = {"hr": 45, "technical": 55, "manager": 90}

HEDGES = ["i think maybe", "not sure", "i guess", "probably", "kind of", "sort of", "i don't know", "i am not certain", "maybe", "i suppose"]
ASSERTIVE = ["i led", "i built", "i implemented", "i designed", "i decided", "i developed", "i created", "i owned", "i improved", "i delivered", "i managed", "i organized"]
STRUCTURE = ["first", "second", "because", "for example", "for instance", "therefore", "as a result", "in addition", "however", "finally", "so that"]

STAR_CUES = {
    "situation": ["when ", "at the time", "we were", "during ", "situation", "project", "in my ", "there was", "faced", "our team"],
    "task": ["responsible", "my role", "my task", "goal", "needed to", "had to", "objective", "assigned", "supposed to", "my job"],
    "action": ["i decided", "i implemented", "i organized", "i built", "i created", "i led", "i worked", "i proposed", "i talked", "i set up", "i started", "i took", "i wrote", "i asked", "i suggested", "i divided"],
    "result": ["result", "as a result", "achieved", "improved", "reduced", "increased", "delivered", "outcome", "learned", "%", "successfully", "finished", "completed", "saved"],
}

WEIGHTS = {
    "hr": {"communication": .25, "clarity": .2, "confidence": .15, "completeness": .2, "relevance": .2},
    "technical": {"technical_accuracy": .3, "concept_understanding": .2, "depth": .15, "problem_solving": .1, "relevance": .1, "completeness": .05, "clarity": .05, "communication": .05},
    "manager": {"situation": .12, "task": .12, "action": .2, "result": .2, "relevance": .12, "communication": .12, "clarity": .06, "completeness": .06},
}


def _clamp(v, lo=0, hi=10) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return float("nan")


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9'’+#-]+", text)


class AnswerEvaluator:
    def __init__(self, llm: OllamaService, embeddings: EmbeddingService):
        self.llm, self.embeddings = llm, embeddings

    # ---------------------------------------------------------------- heuristics
    def heuristic_scores(self, agent: str, question: str, answer: str, role: str = "") -> dict:
        words = _words(answer)
        n = len(words)
        lowered = answer.lower()
        sentences = [s for s in re.split(r"[.!?]+", answer) if s.strip()]
        avg_sentence = n / max(1, len(sentences))
        fillers = sum(count_fillers(answer).values())
        filler_ratio = fillers / max(1, n)
        hedges = sum(lowered.count(h) for h in HEDGES)
        assertive = sum(lowered.count(a) for a in ASSERTIVE)
        structure = sum(1 for s in STRUCTURE if s in lowered)
        diversity = len({w.lower() for w in words}) / max(1, n)

        target = EXPECTED_WORDS[agent]
        completeness = min(10.0, 10.0 * n / target) if n else 0.0
        clarity = 7.0 - (2.0 if avg_sentence > 35 else 0) - (1.0 if avg_sentence < 5 else 0) - min(3.0, filler_ratio * 30) + (1.0 if diversity > 0.6 else 0)
        communication = clarity * 0.7 + min(3.0, structure * 0.8) + (0.5 if len(sentences) >= 3 else 0)
        confidence = 6.0 + min(2.5, assertive * 0.8) - min(4.0, hedges * 1.0) - min(2.0, filler_ratio * 15)

        sim = self.embeddings.similarity(question, answer)
        semantic = self.embeddings.is_semantic()
        relevance = (sim - 0.10) / 0.50 * 10 if semantic else sim * 22 + 2
        relevance = _clamp(relevance)

        scores = {
            "communication": _clamp(communication), "clarity": _clamp(clarity), "confidence": _clamp(confidence),
            "completeness": _clamp(completeness), "relevance": relevance,
        }
        if agent == "hr":
            scores["professionalism"] = _clamp(7.5 - (2.0 if re.search(r"\b(hate|stupid|idiot)\b", lowered) else 0) - min(2.0, filler_ratio * 20))
        elif agent == "technical":
            kws = ROLES.get(role, {}).get("keywords", [])
            hits = sum(1 for k in kws if k in lowered) + len({t for t in _words(question.lower()) if len(t) > 5} & {w.lower() for w in words})
            base = _clamp(min(6.0, 1.5 + hits * 0.9))  # capped: correctness cannot be verified heuristically
            scores.update({"technical_accuracy": min(base, 6.0), "concept_understanding": min(base, 6.0),
                           "problem_solving": _clamp(min(6.0, 2 + structure)), "depth": _clamp(min(6.0, completeness * 0.6 + hits * 0.3))})
        else:
            for k, cues in STAR_CUES.items():
                c = sum(1 for cue in cues if cue in lowered)
                scores[k] = 0.0 if c == 0 else (4.0 if c == 1 else 7.0 if c == 2 else 9.0)
        return scores

    # ----------------------------------------------------------------- LLM part
    def _llm_scores(self, agent: str, question: str, answer: str, role: str) -> dict | None:
        keys = COMMON + EXTRA_KEYS[agent]
        try:
            data = self.llm.generate_json(EVAL_SYSTEM, build_eval_prompt(agent, question, answer, role_label(role)),
                                          required=["clarity", "relevance"], temperature=0.2, max_tokens=450)
        except LLMError as e:
            log_event(log, "evaluation_llm_unavailable", logging.WARNING, reason=type(e).__name__)
            return None
        out = {k: _clamp(data.get(k)) for k in keys}
        out["feedback"] = str(data.get("feedback") or "")[:600]
        out["improvement"] = str(data.get("improvement") or "")[:400]
        out["evidence"] = str(data.get("evidence") or "")[:200]
        return out

    # ------------------------------------------------------------------- public
    def evaluate(self, agent: str, question: str, answer: str, role: str = "software_engineer") -> dict:
        """Return per-metric scores (0-10), overall (0-10), feedback, improvement and method."""
        answer = (answer or "").strip()
        n = len(_words(answer))
        heur = self.heuristic_scores(agent, question, answer, role)
        llm = self._llm_scores(agent, question, answer, role) if n else None

        scores: dict[str, float] = {}
        for key, h in heur.items():
            l = llm.get(key) if llm else None
            if l is None or l != l:  # missing / NaN
                scores[key] = h
            elif key == "relevance":
                scores[key] = LLM_WEIGHT * l + (1 - LLM_WEIGHT) * h
            elif agent == "technical" and key in ("technical_accuracy", "concept_understanding", "problem_solving", "depth"):
                scores[key] = 0.85 * l + 0.15 * h  # LLM judges correctness; heuristic only a light anchor
            else:
                scores[key] = LLM_WEIGHT * l + (1 - LLM_WEIGHT) * h

        # Sanity caps (evidence-based scoring): non-answers cannot score well.
        if n == 0:
            scores = {k: 0.0 for k in scores}
        elif n < 5:
            scores = {k: min(v, 3.0) for k, v in scores.items()}
        elif n < 15:
            scores["completeness"] = min(scores["completeness"], 4.0)
            if agent == "technical":
                scores["depth"] = min(scores["depth"], 4.0)
        if agent == "manager" and n < 30:
            for k in ("situation", "task", "action", "result"):
                scores[k] = min(scores[k], 5.0)

        scores = {k: round(v, 1) for k, v in scores.items()}
        overall = round(sum(scores.get(k, 0) * w for k, w in WEIGHTS[agent].items()) / sum(WEIGHTS[agent].values()), 1)
        method = "llm+heuristic" if llm else "heuristic"
        feedback = (llm or {}).get("feedback") or self._fallback_feedback(agent, scores, n)
        improvement = (llm or {}).get("improvement") or self._fallback_improvement(agent, scores)
        result = {**scores, "overall": overall, "feedback": feedback, "improvement": improvement, "method": method, "word_count": n}
        if llm and llm.get("evidence"):
            result["evidence"] = llm["evidence"]
        if method == "heuristic":
            result["note"] = "Scored with deterministic heuristics only (LLM unavailable); treat as approximate."
        return result

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _fallback_feedback(agent: str, s: dict, n: int) -> str:
        if n == 0:
            return "No answer was provided for this question."
        parts = []
        parts.append("The answer was reasonably detailed." if s["completeness"] >= 6 else "The answer was brief and could cover more ground.")
        parts.append("Delivery was clear." if s["clarity"] >= 6 else "The delivery could be clearer and better structured.")
        if agent == "manager":
            missing = [k.title() for k in ("situation", "task", "action", "result") if s.get(k, 0) < 4]
            if missing:
                parts.append("STAR elements not clearly covered: " + ", ".join(missing) + ".")
        return " ".join(parts)

    @staticmethod
    def _fallback_improvement(agent: str, s: dict) -> str:
        if agent == "manager":
            weakest = min(("situation", "task", "action", "result"), key=lambda k: s.get(k, 0))
            return f"Make the '{weakest}' part of your STAR answer more explicit, with a concrete example."
        if agent == "technical":
            return "Explain the concept, then give a concrete example or trade-off from your own work."
        return "Structure your answer (context, key point, example) and quantify results where possible."
