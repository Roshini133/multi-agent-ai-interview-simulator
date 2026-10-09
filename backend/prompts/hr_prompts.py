"""HR interviewer prompts and fallback question bank."""

HR_SYSTEM = """You are {name}, a professional HR interviewer conducting a realistic online interview for the role of {role}.
Rules:
- Ask exactly ONE question. Do not answer it, do not give feedback or explanations.
- Be polite, professional and concise (max 45 words).
- Choose the question based on the previous answer, interview stage and candidate profile. Do not use a fixed script.
- Never assume facts about the candidate that are not in the provided profile.
- Do not repeat topics already covered.
Respond ONLY as JSON: {{"question": "...", "topic": "short topic label"}}"""

HR_TOPICS = ["introduction", "motivation", "strengths", "weakness", "challenge", "why_hire", "career_goals", "teamwork_culture"]

# (topic, difficulty, question) - used only when the LLM is unavailable or returns an invalid question.
HR_FALLBACK = [
    ("introduction", "EASY", "To begin, could you please tell me about yourself and your background?"),
    ("motivation", "EASY", "What interests you about the {role} role, and why now?"),
    ("strengths", "EASY", "What would you say are your two or three strongest professional qualities? Please give an example."),
    ("weakness", "MEDIUM", "What is one area you are actively working to improve, and what steps are you taking?"),
    ("challenge", "MEDIUM", "Tell me about a difficult situation you handled recently and what you learned from it."),
    ("why_hire", "MEDIUM", "Why should we consider you for this position over other candidates?"),
    ("career_goals", "MEDIUM", "Where do you see yourself professionally in five years?"),
    ("teamwork_culture", "HARD", "Describe the kind of team environment where you do your best work, and how you contribute to it."),
]

HR_FOLLOWUP = "Could you elaborate on that with a specific example from your own experience?"
