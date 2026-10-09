"""Shared behaviour for interviewer agents: LLM question generation with validated fallback + reviews."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from statistics import mean

from prompts.panel_prompts import REVIEW_SYSTEM
from services.embedding_service import EmbeddingService
from services.ollama_service import LLMError, OllamaService
from utils.logging_config import log_event

log = logging.getLogger(__name__)

METRIC_LABELS = {
    "communication": "Communication", "clarity": "Clarity", "confidence": "Confidence", "completeness": "Completeness", "relevance": "Relevance",
    "professionalism": "Professionalism", "technical_accuracy": "Technical accuracy", "concept_understanding": "Concept understanding",
    "problem_solving": "Problem solving", "depth": "Depth", "situation": "STAR - Situation", "task": "STAR - Task", "action": "STAR - Action", "result": "STAR - Result",
}


@dataclass
class QuestionContext:
    role: str
    role_label: str
    candidate_name: str = "Candidate"
    resume: dict = field(default_factory=dict)
    resume_snippets: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)   # this agent's previous turns: question, answer, overall, feedback, topic
    difficulty: str = "MEDIUM"
    action: str = "start"                               # start | increase | maintain | reinforce
    asked_topics: list[str] = field(default_factory=list)
    asked_questions: list[str] = field(default_factory=list)
    number: int = 1
    total: int = 3
    cross_notes: list[str] = field(default_factory=list)  # observations from other agents (cross-agent context)


@dataclass
class QuestionSpec:
    text: str
    topic: str
    difficulty: str
    source: str = "llm"
    resume_grounded: bool = False


class BaseAgent:
    key = "base"
    display_name = "Interviewer"
    title = "Interviewer"

    def __init__(self, session_id: str, llm: OllamaService, embeddings: EmbeddingService):
        self.session_id, self.llm, self.embeddings = session_id, llm, embeddings
        self.asked: list[str] = []  # per-session, per-agent memory of what was asked

    # -- to be provided by subclasses -------------------------------------------------
    def intro(self, ctx: QuestionContext) -> str:  # spoken hand-over line
        return ""

    def system_prompt(self, ctx: QuestionContext) -> str:
        raise NotImplementedError

    def user_prompt(self, ctx: QuestionContext) -> str:
        return self._profile_block(ctx) + self._history_block(ctx)

    def fallback_question(self, ctx: QuestionContext) -> QuestionSpec:
        raise NotImplementedError

    # -- shared helpers ---------------------------------------------------------------
    def _profile_block(self, ctx: QuestionContext) -> str:
        r = ctx.resume or {}
        lines = [f"Candidate name: {ctx.candidate_name}", f"Target role: {ctx.role_label}"]
        if r.get("skills"):
            lines.append("Resume skills: " + ", ".join(r["skills"][:15]))
        if ctx.resume_snippets:
            lines.append("Relevant resume items (only use these facts):\n- " + "\n- ".join(s[:220] for s in ctx.resume_snippets[:3]))
        if not r:
            lines.append("No resume was provided.")
        return "\n".join(lines) + "\n"

    def _history_block(self, ctx: QuestionContext) -> str:
        out = [f"\nQuestion {ctx.number} of {ctx.total} from you. Difficulty: {ctx.difficulty}."]
        if ctx.asked_topics:
            out.append("Topics already covered: " + ", ".join(ctx.asked_topics))
        if ctx.cross_notes:
            out.append("Notes from other panel members: " + " ".join(ctx.cross_notes[:2]))
        for turn in ctx.history[-2:]:
            out.append(f"Previous question: {turn['question']}\nCandidate answer: {turn['answer'][:600]}\n(Score {turn.get('overall', '?')}/10)")
        if ctx.history:
            out.append("If the last answer was vague or incomplete you may ask a focused follow-up; otherwise move to a new topic.")
        return "\n".join(out)

    def _valid(self, text: str, ctx: QuestionContext) -> bool:
        text = (text or "").strip()
        if not (15 <= len(text) <= 450) or "?" not in text:
            return False
        for prev in ctx.asked_questions[-10:]:
            if self.embeddings.similarity(text, prev) > 0.88:
                return False
        return True

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"^(assistant|interviewer|question)\s*[:\-]\s*", "", text.strip(), flags=re.I)
        return text.strip().strip('"').strip()

    # -- public API -------------------------------------------------------------------
    def generate_question(self, ctx: QuestionContext) -> QuestionSpec:
        try:
            data = self.llm.generate_json(self.system_prompt(ctx), self.user_prompt(ctx), required=["question"], temperature=0.7, max_tokens=200)
            text = self._clean(str(data.get("question", "")))
            if self._valid(text, ctx):
                topic = str(data.get("topic") or "general")[:60]
                grounded = any(s[:25].lower() in text.lower() for s in ctx.resume_snippets) if ctx.resume_snippets else False
                log_event(log, "question_generated", agent=self.key, source="llm", difficulty=ctx.difficulty)
                self.asked.append(text)
                return QuestionSpec(text, topic, ctx.difficulty, "llm", grounded)
            log_event(log, "question_rejected", logging.WARNING, agent=self.key)
        except LLMError as e:
            log_event(log, "question_llm_failed", logging.WARNING, agent=self.key, reason=type(e).__name__)
        spec = self.fallback_question(ctx)
        log_event(log, "question_generated", agent=self.key, source="fallback", difficulty=spec.difficulty)
        self.asked.append(spec.text)
        return spec

    def review(self, role_label: str, items: list[dict]) -> dict:
        """Deterministic score/strengths/concerns (from evaluations) + LLM-written narrative with fallback."""
        answered = [i for i in items if i.get("scores")]
        if not answered:
            return {"agent": self.key, "name": self.display_name, "title": self.title, "score": None, "answered": 0,
                    "summary": "No answers were recorded for this part of the interview.", "strengths": [], "concerns": [], "metrics": {}}
        metric_keys = sorted({k for i in answered for k in i["scores"] if k in METRIC_LABELS})
        means = {k: round(mean(i["scores"][k] for i in answered if k in i["scores"]), 1) for k in metric_keys}
        score = round(mean(i["overall"] for i in answered) * 10, 1)
        strengths = [f"{METRIC_LABELS[k]} ({v}/10)" for k, v in sorted(means.items(), key=lambda kv: -kv[1]) if v >= 7][:3]
        concerns = [f"{METRIC_LABELS[k]} ({v}/10)" for k, v in sorted(means.items(), key=lambda kv: kv[1]) if v < 5.5][:3]
        summary = None
        try:
            metrics_txt = "; ".join(f"{METRIC_LABELS[k]} {v}/10" for k, v in means.items())
            fb = " | ".join(i.get("feedback", "")[:160] for i in answered[:4])
            data = self.llm.generate_json(REVIEW_SYSTEM.format(name=self.title), f"Role: {role_label}\nAverage metrics: {metrics_txt}\nAnswer feedback: {fb}",
                                          required=["summary"], temperature=0.4, max_tokens=200)
            summary = str(data["summary"]).strip()[:600] or None
        except LLMError:
            pass
        if not summary:
            summary = self._template_summary(score, strengths, concerns)
        return {"agent": self.key, "name": self.display_name, "title": self.title, "score": score, "answered": len(answered),
                "summary": summary, "strengths": strengths, "concerns": concerns, "metrics": means}

    def _template_summary(self, score: float, strengths: list[str], concerns: list[str]) -> str:
        level = "strong" if score >= 75 else "solid" if score >= 60 else "developing" if score >= 45 else "early-stage"
        s = f"Overall {level} performance in the {self.title.lower()} round ({score}/100)."
        if strengths:
            s += " Strengths: " + ", ".join(strengths) + "."
        if concerns:
            s += " Areas to improve: " + ", ".join(concerns) + "."
        return s
