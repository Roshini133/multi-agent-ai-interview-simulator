"""Prompt for answer evaluation (shared by all agents)."""

EVAL_SYSTEM = (
    "You are a strict, fair interview evaluator. Score ONLY what the candidate actually said. "
    "Never invent or assume experiences, skills or facts that are not in the answer. "
    "If the answer is empty, evasive or off-topic, give scores of 2 or below. "
    "Respond with a single JSON object and nothing else."
)

RUBRICS = {
    "hr": "Also score professionalism (tone, respect, appropriateness).",
    "technical": "Also score technical_accuracy (are the statements correct?), concept_understanding, problem_solving (reasoning/approach) and depth (detail beyond definitions).",
    "manager": "Also score STAR elements from 0-10 each: situation, task, action, result (0 = element absent from the answer).",
}

EXTRA_KEYS = {
    "hr": ["professionalism"],
    "technical": ["technical_accuracy", "concept_understanding", "problem_solving", "depth"],
    "manager": ["situation", "task", "action", "result"],
}


def build_eval_prompt(agent: str, question: str, answer: str, role_label: str) -> str:
    keys = ["communication", "clarity", "confidence", "completeness", "relevance"] + EXTRA_KEYS[agent]
    schema = ", ".join(f'"{k}": <0-10 integer>' for k in keys)
    return (
        f"Role being interviewed for: {role_label}\n"
        f"Interviewer type: {agent}\n\n"
        f"Question:\n{question}\n\n"
        f"Candidate answer:\n\"\"\"\n{answer}\n\"\"\"\n\n"
        f"Score 0-10 (integers) for communication, clarity, confidence (as evidenced by assertive, specific language), completeness and relevance. {RUBRICS[agent]}\n"
        f"Return JSON: {{{schema}, \"feedback\": \"2 sentences citing what the answer did or missed\", "
        f"\"improvement\": \"one concrete suggestion\", \"evidence\": \"a short phrase quoted from the answer, or empty\"}}"
    )
