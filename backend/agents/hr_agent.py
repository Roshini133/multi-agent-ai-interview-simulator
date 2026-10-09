"""HR interviewer: communication, motivation, culture fit. (Refactored from the original prototype HRAgent.)"""
from __future__ import annotations

from agents.base_agent import BaseAgent, QuestionContext, QuestionSpec
from prompts.hr_prompts import HR_FALLBACK, HR_FOLLOWUP, HR_SYSTEM, HR_TOPICS


class HRAgent(BaseAgent):
    key = "hr"
    display_name = "Priya Nair"
    title = "HR Interviewer"

    def intro(self, ctx: QuestionContext) -> str:
        return (f"Hello {ctx.candidate_name.split()[0]}, welcome to your interview practice session. I'm {self.display_name} from HR. "
                f"We'll start with a few questions about you and your motivation for the {ctx.role_label} role.")

    def system_prompt(self, ctx: QuestionContext) -> str:
        return HR_SYSTEM.format(name=self.display_name, role=ctx.role_label)

    def fallback_question(self, ctx: QuestionContext) -> QuestionSpec:
        last = ctx.history[-1] if ctx.history else None
        # Weak, thin previous answer -> ask for a concrete example instead of moving on (adaptive follow-up).
        if last and last.get("overall", 10) < 4.5 and last.get("topic") != "followup" and last.get("word_count", 99) < 25:
            return QuestionSpec(HR_FOLLOWUP, "followup", ctx.difficulty, "fallback")
        remaining = [t for t in HR_FALLBACK if t[0] not in ctx.asked_topics]
        if not remaining:
            remaining = HR_FALLBACK
        # Prefer topics at or below the current difficulty, but keep the natural order.
        order = ["EASY", "MEDIUM", "HARD"]
        eligible = [t for t in remaining if order.index(t[1]) <= order.index(ctx.difficulty)] or remaining
        topic, diff, text = eligible[0]
        grounded = False
        if topic == "motivation" and ctx.resume.get("projects"):
            text += f" Your resume mentions \"{ctx.resume['projects'][0][:70]}\" - how did that shape your interest?"
            grounded = True
        return QuestionSpec(text.format(role=ctx.role_label), topic, ctx.difficulty, "fallback", grounded)
