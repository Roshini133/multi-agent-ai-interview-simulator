from flask import Flask, jsonify, request
from flask_cors import CORS
from services.session_manager import SessionManager

from agents.hr_agent import HRAgent
from services.answer_evaluator import AnswerEvaluator

app = Flask(__name__)
CORS(app)

hr_agent = HRAgent()
answer_evaluator = AnswerEvaluator()
session_manager = SessionManager()


@app.route("/")
def home():
    return jsonify({
        "message": "AI Interview Simulator Backend Running"
    })


@app.route("/api/hr/interview", methods=["POST"])
def hr_interview():

    data = request.get_json() or {}

    session_id = data.get("session_id")
    answer = data.get("answer")

    # Check session ID
    if not session_id:
        return jsonify({
            "error": "session_id is required"
        }), 400

    # Check whether session exists
    if not session_manager.session_exists(session_id):
        return jsonify({
            "error": "Invalid session_id"
        }), 404

    # Get the HR agent belonging to this session
    session_hr_agent = session_manager.get_hr_agent(session_id)

    # First question
    if not answer:
        question = session_hr_agent.next_question()

        return jsonify({
            "session_id": session_id,
            "question": question
        })

    # Get previous question
    previous_question = ""

    for message in reversed(session_hr_agent.messages):
        if message["role"] == "assistant":
            previous_question = message["content"]
            break

    # Evaluate candidate answer
    evaluation = answer_evaluator.evaluate(
        previous_question,
        answer
    )

    # Generate next question
    next_question = session_hr_agent.next_question(answer)

    return jsonify({
        "session_id": session_id,
        "question": next_question,
        "evaluation": evaluation
    })
@app.route("/api/interview/start", methods=["POST"])
def start_interview():
    session_id = session_manager.create_session()

    return jsonify({
        "session_id": session_id,
        "status": "active"
    })


if __name__ == "__main__":
    app.run(debug=True)