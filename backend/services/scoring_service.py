"""Transparent scoring: every number in the final report can be traced to these formulas."""
from __future__ import annotations

from statistics import mean

CATEGORY_WEIGHTS = {"hr_communication": 0.20, "technical": 0.35, "managerial": 0.25, "behavioral": 0.10, "resume_relevance": 0.10}
CATEGORY_LABELS = {
    "hr_communication": "HR / Communication", "technical": "Technical", "managerial": "Managerial",
    "behavioral": "Behavioral (STAR)", "resume_relevance": "Resume Relevance",
}
SCORING_METHOD = (
    "Each answer receives 0-10 metric scores (LLM rubric blended 70/30 with deterministic heuristics). Answer overall = weighted metric average per interviewer type. "
    "Category score = mean answer overall x 10. Overall = weighted mean of available categories (HR 20%, Technical 35%, Managerial 25%, Behavioral/STAR 10%, Resume relevance 10%), "
    "re-normalised when a category has no data. Webcam/integrity signals are informational only and are NOT included in any score."
)
ADVICE = {
    "communication": "Practise structuring answers (context -> key point -> example -> result).",
    "clarity": "Use shorter sentences and signpost your points ('first', 'second', 'as a result').",
    "confidence": "Use decisive, specific language ('I built', 'I decided') and reduce hedging words.",
    "completeness": "Aim for fuller answers with a concrete example, not just a definition.",
    "relevance": "Answer the exact question first, then add supporting detail.",
    "technical_accuracy": "Revise core concepts for the role and verify your explanations against documentation.",
    "depth": "Go beyond definitions: explain trade-offs, edge cases and practical experience.",
    "concept_understanding": "Practise explaining fundamentals in simple terms with examples.",
    "problem_solving": "Talk through your reasoning step by step before giving the final answer.",
    "situation": "Open behavioural answers with clear context (who, what, when).",
    "task": "State your specific responsibility or goal explicitly.",
    "action": "Describe what YOU personally did, step by step.",
    "result": "Close with a measurable outcome and what you learned.",
}


def _pct(vals: list[float]) -> float | None:
    return round(mean(vals) * 10, 1) if vals else None


def compute_scores(items: list[dict]) -> dict:
    """items: [{agent, topic, difficulty, scores{...}, overall, resume_alignment?, word_count?, index}]"""
    answered = [i for i in items if i.get("scores")]
    by_agent = {a: [i for i in answered if i["agent"] == a] for a in ("hr", "technical", "manager")}

    star_vals = [mean(i["scores"][k] for k in ("situation", "task", "action", "result") if k in i["scores"]) for i in by_agent["manager"] if "situation" in i["scores"]]
    align = [i["resume_alignment"] for i in answered if i.get("resume_alignment") is not None]
    categories = {
        "hr_communication": _pct([i["overall"] for i in by_agent["hr"]]),
        "technical": _pct([i["overall"] for i in by_agent["technical"]]),
        "managerial": _pct([i["overall"] for i in by_agent["manager"]]),
        "behavioral": _pct(star_vals),
        "resume_relevance": _pct(align),
    }
    avail = {k: v for k, v in categories.items() if v is not None}
    overall = round(sum(v * CATEGORY_WEIGHTS[k] for k, v in avail.items()) / sum(CATEGORY_WEIGHTS[k] for k in avail), 1) if avail else None

    def metric_mean(key: str, pool=answered):
        vals = [i["scores"][key] for i in pool if key in i["scores"]]
        return round(mean(vals), 1) if vals else None

    competencies = {k: metric_mean(k) for k in ("communication", "clarity", "confidence", "completeness", "relevance")}
    competencies["technical_accuracy"] = metric_mean("technical_accuracy", by_agent["technical"])

    all_metric_means = {}
    for key in ADVICE:
        m = metric_mean(key)
        if m is not None:
            all_metric_means[key] = m
    label = lambda k: k.replace("_", " ").title()
    strengths = [f"{label(k)} ({v}/10)" for k, v in sorted(all_metric_means.items(), key=lambda kv: -kv[1]) if v >= 7][:5]
    weak = sorted([(k, v) for k, v in all_metric_means.items() if v < 6.5], key=lambda kv: kv[1])[:5]
    improvements = [f"{label(k)} ({v}/10) - {ADVICE[k]}" for k, v in weak]

    weak_topics = [i["topic"] for i in by_agent["technical"] if i["overall"] < 6 and i.get("topic") and i["topic"] not in ("resume_project", "general")]
    prep_topics = list(dict.fromkeys(t.replace("_", " ").title() for t in weak_topics))[:6]

    progression = [{"index": n + 1, "agent": i["agent"], "score": round(i["overall"] * 10, 1), "difficulty": i.get("difficulty"), "topic": i.get("topic")}
                   for n, i in enumerate(sorted(answered, key=lambda x: x.get("index", 0)))]
    return {
        "overall": overall, "categories": categories, "category_labels": CATEGORY_LABELS, "weights": CATEGORY_WEIGHTS,
        "agent_scores": {a: _pct([i["overall"] for i in by_agent[a]]) for a in by_agent},
        "competencies": competencies, "strengths": strengths, "improvements": improvements,
        "prep_topics": prep_topics, "progression": progression, "method": SCORING_METHOD, "questions_answered": len(answered),
    }
