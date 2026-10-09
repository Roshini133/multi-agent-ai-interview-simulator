import ollama
import json


class AnswerEvaluator:

    def evaluate(self, question, answer):

        prompt = f"""
You are an expert interview evaluator.

Evaluate the candidate's answer based on the interview question.

Interview Question:
{question}

Candidate Answer:
{answer}

Give scores from 0 to 10 for:

1. Communication
2. Clarity
3. Confidence
4. Completeness
5. Relevance

Also provide:
- Overall feedback
- One improvement suggestion

Return ONLY valid JSON in this format:

{{
    "communication": 0,
    "clarity": 0,
    "confidence": 0,
    "completeness": 0,
    "relevance": 0,
    "feedback": "short feedback",
    "improvement": "one improvement suggestion"
}}
"""

        response = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        result = response["message"]["content"].strip()

        # Remove markdown code block if LLM adds it
        if result.startswith("```"):
            result = result.replace("```json", "")
            result = result.replace("```", "")
            result = result.strip()

        return json.loads(result)