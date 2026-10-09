"""Technical interviewer: role-specific, resume-personalised, difficulty-adaptive."""
from __future__ import annotations

from agents.base_agent import BaseAgent, QuestionContext, QuestionSpec
from prompts.technical_prompts import ACTION_RULES, RESUME_PROBES, TECH_FALLBACK as _BANK, TECH_SYSTEM


class TechnicalAgent(BaseAgent):
    key = "technical"
    display_name = "Arjun Mehta"
    title = "Technical Interviewer"

    def intro(self, ctx: QuestionContext) -> str:
        return (f"Thank you. I'm {self.display_name}, a senior engineer on the panel. "
                f"I'll now ask some technical questions for the {ctx.role_label} role. Please think aloud and explain your reasoning.")

    def system_prompt(self, ctx: QuestionContext) -> str:
        return TECH_SYSTEM.format(name=self.display_name, role=ctx.role_label, difficulty=ctx.difficulty,
                                  action_rule=ACTION_RULES.get(ctx.action, ACTION_RULES["maintain"]))

    def fallback_question(self, ctx: QuestionContext) -> QuestionSpec:
        # Resume personalisation: every other question probes a resume project/experience when available.
        items = (ctx.resume.get("projects") or []) + (ctx.resume.get("internships") or [])
        probe_turn = ctx.number % 2 == 0 and items and ctx.action != "reinforce"
        if probe_turn:
            idx = (ctx.number // 2 - 1) % len(items)
            item = items[idx][:90].rstrip(" .,;")
            return QuestionSpec(RESUME_PROBES[idx % len(RESUME_PROBES)].format(item=item), "resume_project", ctx.difficulty, "fallback", True)
        bank = _BANK.get(ctx.role, _BANK["software_engineer"])
        pool = bank[ctx.difficulty]
        unused = [q for q in pool if q[1] not in ctx.asked_questions]
        if ctx.action == "reinforce" and ctx.asked_topics:
            same_topic = [q for q in unused if q[0] == ctx.asked_topics[-1]]
            unused = same_topic or unused
        if not unused:  # exhausted this level: borrow from other levels
            unused = [q for lvl in ("EASY", "MEDIUM", "HARD") for q in bank[lvl] if q[1] not in ctx.asked_questions] or pool
        fresh_topics = [q for q in unused if q[0] not in ctx.asked_topics] or unused
        topic, text = fresh_topics[0]
        return QuestionSpec(text, topic, ctx.difficulty, "fallback", False)
