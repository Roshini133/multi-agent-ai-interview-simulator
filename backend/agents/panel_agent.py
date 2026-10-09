"""Panel agent: combines HR/Technical/Manager reviews into a balanced assessment (never a hire decision)."""
from __future__ import annotations

import logging

from prompts.panel_prompts import PANEL_SYSTEM
from services.ollama_service import LLMError, OllamaService

log = logging.getLogger(__name__)


def readiness_level(score: float | None) -> str:
    if score is None:
        return "Not enough data"
    if score >= 80:
        return "Interview-ready"
    if score >= 65:
        return "Nearly ready"
    if score >= 50:
        return "Developing"
    return "Needs more practice"


class PanelAgent:
    key = "panel"
    display_name = "Interview Panel"
    title = "Panel Moderator"

    def __init__(self, llm: OllamaService):
        self.llm = llm

    def discuss(self, role_label: str, reviews: dict[str, dict], overall: float | None, behavior_note: str) -> dict:
        spread_info = self._disagreement(reviews)
        discussion, assessment, source = None, None, "deterministic"
        try:
            brief = "\n".join(f"{r['title']} (score {r['score']}/100): {r['summary']}" for r in reviews.values() if r.get("score") is not None)
            user = f"Role: {role_label}\nOverall practice score: {overall}/100\n{brief}\nDisagreement note: {spread_info or 'none'}\nBehaviour note: {behavior_note}"
            data = self.llm.generate_json(PANEL_SYSTEM, user, required=["discussion", "final_assessment"], temperature=0.4, max_tokens=650)
            disc = [{"speaker": str(d.get("speaker", ""))[:20], "message": str(d.get("message", ""))[:400]}
                    for d in data["discussion"] if isinstance(d, dict) and d.get("message")]
            if disc and str(data["final_assessment"]).strip():
                discussion, assessment, source = disc[:6], str(data["final_assessment"]).strip()[:900], "llm"
        except LLMError:
            pass
        if not discussion:
            discussion = self._template_discussion(reviews, spread_info)
            assessment = self._template_assessment(role_label, overall, reviews, spread_info)
        return {"discussion": discussion, "final_assessment": assessment, "readiness": readiness_level(overall),
                "disagreement": spread_info, "source": source,
                "disclaimer": "This is an interview practice assessment, not an employment decision."}

    @staticmethod
    def _disagreement(reviews: dict[str, dict]) -> str | None:
        scored = {k: r["score"] for k, r in reviews.items() if r.get("score") is not None}
        if len(scored) < 2:
            return None
        hi, lo = max(scored, key=scored.get), min(scored, key=scored.get)
        if scored[hi] - scored[lo] >= 15:
            return f"{reviews[hi]['title']} ({scored[hi]}) and {reviews[lo]['title']} ({scored[lo]}) differ by {round(scored[hi] - scored[lo])} points; both views are weighted in the overall score."
        return None

    @staticmethod
    def _template_discussion(reviews: dict[str, dict], spread: str | None) -> list[dict]:
        names = {"hr": "HR", "technical": "Technical", "manager": "Manager"}
        out = [{"speaker": names[k], "message": r["summary"]} for k, r in reviews.items() if r.get("score") is not None]
        if spread:
            out.append({"speaker": "Manager", "message": "We saw a noticeable difference between rounds. " + spread})
        return out

    @staticmethod
    def _template_assessment(role_label: str, overall: float | None, reviews: dict[str, dict], spread: str | None) -> str:
        if overall is None:
            return "There was not enough interview data to produce a balanced assessment."
        strong = [r["title"] for r in reviews.values() if (r.get("score") or 0) >= 70]
        weak = [r["title"] for r in reviews.values() if r.get("score") is not None and r["score"] < 55]
        s = f"For the {role_label} practice interview, the panel's balanced score is {overall}/100 ({readiness_level(overall)})."
        if strong:
            s += " Stronger areas: " + ", ".join(strong) + "."
        if weak:
            s += " Priority areas: " + ", ".join(weak) + "."
        if spread:
            s += " " + spread
        return s + " These are practice-feedback scores and no single interviewer's view was allowed to override the others."
