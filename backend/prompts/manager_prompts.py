"""Hiring-manager prompts and behavioural fallback bank."""

MANAGER_SYSTEM = """You are {name}, a hiring manager interviewing a candidate for a {role} position.
Rules:
- Ask exactly ONE realistic behavioural question that invites a STAR answer (Situation, Task, Action, Result).
- Focus on leadership, teamwork, conflict, decision making, ownership, time management or handling pressure.
- Difficulty {difficulty}: EASY = common scenario, MEDIUM = involves trade-offs, HARD = ambiguity, high stakes or pressure.
- Do not give feedback or answers. Max 45 words. Do not assume experiences not in the profile. Do not repeat topics.
{cross_note}
Respond ONLY as JSON: {{"question": "...", "topic": "short topic label"}}"""

MANAGER_TOPICS = ["teamwork", "conflict", "time_management", "ownership", "decision_making", "pressure", "leadership"]

MANAGER_FALLBACK = {
    "teamwork": {"EASY": "Tell me about a time you worked in a team to achieve a goal. What was your contribution?",
                 "MEDIUM": "Describe a time a teammate was not pulling their weight. How did you handle it?",
                 "HARD": "Tell me about a time you had to align a team with conflicting priorities without formal authority."},
    "conflict": {"EASY": "Describe a disagreement you had with a colleague and how it was resolved.",
                 "MEDIUM": "Tell me about a time you disagreed with a technical or project decision. What did you do?",
                 "HARD": "Describe a conflict where both sides had valid points and the outcome mattered. How did you resolve it?"},
    "time_management": {"EASY": "Tell me about a time you had to meet a tight deadline. How did you plan your work?",
                        "MEDIUM": "Describe a time you had several competing deadlines. How did you prioritise?",
                        "HARD": "Tell me about a time a deadline became impossible mid-project. What did you do and what was the result?"},
    "ownership": {"EASY": "Tell me about something you took responsibility for without being asked.",
                  "MEDIUM": "Describe a time you made a mistake at work or in a project. How did you handle it?",
                  "HARD": "Tell me about a project that failed or missed its goals. What was your role and what changed afterwards?"},
    "decision_making": {"EASY": "Describe an important decision you made recently and how you reached it.",
                        "MEDIUM": "Tell me about a decision you made with incomplete information. What was the outcome?",
                        "HARD": "Describe a high-stakes decision where you had to choose between two poor options. How did you decide?"},
    "pressure": {"EASY": "How do you handle stressful situations? Please share a specific example.",
                 "MEDIUM": "Tell me about a time you had to deliver under pressure. What did you do?",
                 "HARD": "Describe a crisis you had to handle with limited time and resources. What actions did you take and what happened?"},
    "leadership": {"EASY": "Tell me about a time you took the lead on a task or project.",
                   "MEDIUM": "Describe a time you motivated others or mentored a teammate.",
                   "HARD": "Tell me about leading a team through significant change or setback. What was the result?"},
}
STAR_FOLLOWUPS = {
    "situation": "Could you describe the situation and context in a little more detail?",
    "task": "What was your specific responsibility or goal in that situation?",
    "action": "What specific actions did you personally take?",
    "result": "What was the outcome, and how did you measure or verify it?",
}
