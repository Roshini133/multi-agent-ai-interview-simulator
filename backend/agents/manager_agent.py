"""Manager interviewer: behavioural (STAR) questions."""
from __future__ import annotations

from agents.base_agent import BaseAgent, QuestionContext, QuestionSpec
from prompts.manager_prompts import MANAGER_FALLBACK, MANAGER_SYSTEM, MANAGER_TOPICS, STAR_FOLLOWUPS


class ManagerAgent(BaseAgent):
    key = "manager"
    display_name = "Sarah Thompson"
    title = "Hiring Manager"

    def intro(self, ctx: QuestionContext) -> str:
        return (f"Thanks for those answers. I'm {self.display_name}, the hiring manager. "
                "Now I'd like to understand how you work with others. Please answer using real examples: the situation, your task, your actions and the result.")

    def system_prompt(self, ctx: QuestionContext) -> str:
        note = ""
        if ctx.cross_notes:
            note = "Panel context (use only to choose a relevant behavioural angle, do not mention scores): " + ctx.cross_notes[0]
        return MANAGER_SYSTEM.format(name=self.display_name, role=ctx.role_label, difficulty=ctx.difficulty, cross_note=note)

    def fallback_question(self, ctx: QuestionContext) -> QuestionSpec:
        last = ctx.history[-1] if ctx.history else None
        if last and last.get("weak_star") and last.get("topic") != "followup":
            return QuestionSpec(STAR_FOLLOWUPS[last["weak_star"]], "followup", ctx.difficulty, "fallback")
        topics = [t for t in MANAGER_TOPICS if t not in ctx.asked_topics] or MANAGER_TOPICS
        topic = topics[0]
        return QuestionSpec(MANAGER_FALLBACK[topic][ctx.difficulty], topic, ctx.difficulty, "fallback")
