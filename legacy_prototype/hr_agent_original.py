import ollama

SYSTEM_PROMPT = """
You are a professional HR interviewer.

Rules:
- Ask only ONE question at a time.
- Wait for the candidate's answer before asking the next question.
- Keep the interview realistic, professional, and polite.
- Ask around 5 HR interview questions in sequence.
- Do not give answers or explanations.
"""


class HRAgent:
    def __init__(self):
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def next_question(self, candidate_answer=None):
        # First call -> start interview
        if candidate_answer:
            self.messages.append({
                "role": "user",
                "content": candidate_answer
            })
        else:
            self.messages.append({
                "role": "user",
                "content": "Start the HR interview by asking only the first HR question."
            })

        response = ollama.chat(
            model="llama3.2:3b",
            messages=self.messages
        )

        question = response["message"]["content"].strip()

        # Remove unwanted "assistant" prefix
        if question.lower().startswith("assistant"):
            question = question.split("\n", 1)[-1].strip()
            question = question.lstrip(":").strip()
            question = question.strip('"')

        # Save assistant question in conversation memory
        self.messages.append({
            "role": "assistant",
            "content": question
        })

        return question