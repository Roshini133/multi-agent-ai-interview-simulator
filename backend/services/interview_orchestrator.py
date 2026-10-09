"""Interview orchestrator: owns the interview state machine.

    HR agent -> Technical agent -> Manager agent -> Panel discussion -> Final report

State that must survive restarts (difficulty per agent, adaptation log, stage counters) is stored on the
``InterviewSession`` row; agent objects are per-session and re-created on demand.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from agents.base_agent import QuestionContext, QuestionSpec
from agents.panel_agent import readiness_level
from database import db, json_set
from models import Answer, Evaluation, FinalReport, InterviewSession, Question, ResumeData
from services import adaptive_questioning as adaptive
from services.answer_evaluator import AnswerEvaluator
from services.behavioral_analysis import summarize_integrity
from services.embedding_service import EmbeddingService
from services.resume_parser import resume_chunks
from services.scoring_service import compute_scores
from services.session_manager import SessionManager
from services.voice_service import speech_metrics
from utils.errors import AppError
from utils.logging_config import log_event
from utils.roles import is_valid_role, role_label

log = logging.getLogger(__name__)

START_DIFFICULTY = {"hr": "EASY", "technical": "MEDIUM", "manager": "MEDIUM"}
STAR = ("situation", "task", "action", "result")
AI_COMPONENTS = {
    "pretrained_models": ["Llama 3.2 3B via Ollama (question generation, rubric scoring, narratives)", "Sentence-Transformers all-MiniLM-L6-v2 (semantic similarity, resume retrieval)",
                          "MediaPipe FaceLandmarker / OpenCV Haar cascades (face + head pose)", "faster-whisper (optional speech-to-text)"],
    "deterministic_algorithms": ["Resume section/skill extraction", "Heuristic answer metrics (length, structure, fillers, STAR cues)", "Behavioural event debouncing and counters"],
    "scoring_logic": ["Weighted per-answer overall scores", "Adaptive difficulty engine", "Category-weighted overall score"],
}
DISCLAIMERS = [
    "This is an interview practice assessment, not an employment decision. AI scores are approximate.",
    "Webcam, gaze and browser signals are approximate observations, not proof of cheating or dishonesty, and do not affect scores.",
]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _scale_similarity(sim: float, semantic: bool) -> float:
    v = (sim - 0.10) / 0.50 * 10 if semantic else sim * 22 + 2
    return round(max(0.0, min(10.0, v)), 1)


class InterviewOrchestrator:
    def __init__(self, config, sessions: SessionManager, evaluator: AnswerEvaluator, embeddings: EmbeddingService):
        self.cfg, self.sessions, self.evaluator, self.embeddings = config, sessions, evaluator, embeddings

    # ------------------------------------------------------------------ setup
    @property
    def plan(self) -> list[tuple[str, int]]:
        p = [("hr", self.cfg["HR_QUESTIONS"]), ("technical", self.cfg["TECHNICAL_QUESTIONS"]), ("manager", self.cfg["MANAGER_QUESTIONS"])]
        return [(a, n) for a, n in p if n > 0]

    @property
    def total_questions(self) -> int:
        return sum(n for _, n in self.plan)

    def create_session(self, user, role: str, settings: dict | None = None) -> InterviewSession:
        if not is_valid_role(role):
            raise AppError("invalid_role", "Unknown job role.", 400)
        s = InterviewSession(user_id=user.id, role=role, status="created", settings=settings or {},
                             state={"difficulty": dict(START_DIFFICULTY), "last_action": {}, "adaptation_log": [], "transitions": []})
        db.session.add(s)
        db.session.commit()
        self.sessions.panel_for(s.id)
        log_event(log, "session_created", session_id=s.id, role=role)
        return s

    def attach_resume(self, session: InterviewSession, filename: str, text: str, parsed: dict) -> ResumeData:
        if session.status != "created":
            raise AppError("interview_started", "The resume can only be uploaded before the interview starts.", 409)
        if session.resume:
            db.session.delete(session.resume)
            db.session.flush()
        r = ResumeData(session_id=session.id, filename=filename, raw_text=text, parsed=parsed)
        db.session.add(r)
        db.session.commit()
        log_event(log, "resume_parsed", session_id=session.id, sections=parsed.get("sections_found"), skills=len(parsed.get("skills", [])))
        return r

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _state(session: InterviewSession) -> dict:
        st = dict(session.state or {})
        st.setdefault("difficulty", dict(START_DIFFICULTY))
        st.setdefault("last_action", {})
        st.setdefault("adaptation_log", [])
        st.setdefault("transitions", [])
        return st

    def _stage(self, session: InterviewSession) -> tuple[str | None, int, int]:
        """Return (active agent, questions already asked by it, planned count)."""
        for agent, n in self.plan:
            asked = sum(1 for q in session.questions if q.agent == agent)
            if asked < n:
                return agent, asked, n
        return None, 0, 0

    def _agent_history(self, session: InterviewSession, agent: str) -> list[dict]:
        out = []
        for q in session.questions:
            if q.agent == agent and q.answer and q.answer.evaluation:
                ev = q.answer.evaluation
                sc = ev.scores or {}
                weak = None
                if agent == "manager":
                    star = {k: sc.get(k, 10) for k in STAR}
                    k = min(star, key=star.get)
                    weak = k if star[k] < 4 else None
                out.append({"question": q.text, "answer": q.answer.text, "overall": ev.overall, "feedback": ev.feedback, "topic": q.topic,
                            "difficulty": q.difficulty, "scores": sc, "word_count": sc.get("word_count", 99), "weak_star": weak})
        return out

    def _cross_notes(self, session: InterviewSession, agent: str) -> list[str]:
        notes = []
        if agent == "manager":
            weak = [q.topic for q in session.questions if q.agent == "technical" and q.answer and q.answer.evaluation and q.answer.evaluation.overall < 5 and q.topic]
            if weak:
                notes.append(f"The technical interviewer found gaps in: {', '.join(dict.fromkeys(weak))}. A question about learning from gaps or asking for help may be relevant.")
        if agent == "technical":
            hr = [q.answer.evaluation for q in session.questions if q.agent == "hr" and q.answer and q.answer.evaluation]
            if hr and sum(e.scores.get("completeness", 5) for e in hr) / len(hr) < 5:
                notes.append("HR noted that the candidate's answers were brief; encourage detailed explanations.")
        return notes

    def _resume_snippets(self, session: InterviewSession, agent: str, topic_hint: str) -> list[str]:
        parsed = session.resume.parsed if session.resume else {}
        chunks = resume_chunks(parsed or {})
        if not chunks:
            return []
        k = {"technical": 3, "hr": 1, "manager": 1}[agent]
        query = f"{role_label(session.role)} {topic_hint} " + " ".join((parsed.get("skills") or [])[:8])
        return [c for c, _ in self.embeddings.top_k(query, chunks, k)]

    @staticmethod
    def _serialize_question(q: Question, number: int, stage_no: int, stage_total: int, total: int, agent_obj) -> dict:
        return {"id": q.id, "index": q.index, "agent": q.agent, "agent_name": agent_obj.display_name, "agent_title": agent_obj.title,
                "text": q.text, "topic": q.topic, "difficulty": q.difficulty, "question_number": number, "total_questions": total,
                "stage_number": stage_no, "stage_total": stage_total, "intro": q.intro, "source": q.source, "resume_grounded": bool(q.resume_grounded)}

    # ------------------------------------------------------------- question flow
    def next_question(self, session: InterviewSession) -> dict | None:
        """Return the pending (unanswered) question, or generate the next one. ``None`` = interview finished."""
        if session.status == "completed":
            raise AppError("interview_completed", "This interview has already been completed.", 409)
        panel = self.sessions.panel_for(session.id)
        qs = session.questions
        if qs and qs[-1].answer is None:  # idempotent: page refresh returns the same question
            q = qs[-1]
            agent, stage_no, stage_total = q.agent, sum(1 for x in qs if x.agent == q.agent), dict(self.plan)[q.agent]
            return self._serialize_question(q, q.index, stage_no, stage_total, self.total_questions, panel.get(agent))

        agent_key, asked, planned = self._stage(session)
        if agent_key is None:
            return None
        if session.status == "created":
            session.status, session.started_at = "active", _now()
            log_event(log, "interview_started", session_id=session.id)

        agent = panel.get(agent_key)
        state = self._state(session)
        history = self._agent_history(session, agent_key)
        diff = state["difficulty"].get(agent_key, "MEDIUM")
        ctx = QuestionContext(
            role=session.role, role_label=role_label(session.role), candidate_name=session.user.name,
            resume=(session.resume.parsed if session.resume else {}) or {},
            resume_snippets=self._resume_snippets(session, agent_key, history[-1]["topic"] if history else ""),
            history=history, difficulty=diff, action=state["last_action"].get(agent_key, "start"),
            asked_topics=[q.topic for q in qs if q.agent == agent_key and q.topic], asked_questions=[q.text for q in qs if q.agent == agent_key],
            number=asked + 1, total=planned, cross_notes=self._cross_notes(session, agent_key))
        agent.asked = list(ctx.asked_questions)  # rebuild per-session agent memory after a restart
        spec: QuestionSpec = agent.generate_question(ctx)

        intro = None
        if asked == 0:
            intro = agent.intro(ctx)
            prev = qs[-1].agent if qs else None
            state["transitions"] = state["transitions"] + [{"from": prev, "to": agent_key, "at_question": len(qs) + 1}]
            log_event(log, "agent_transition", session_id=session.id, from_agent=prev, to_agent=agent_key)
        q = Question(session_id=session.id, index=len(qs) + 1, agent=agent_key, text=spec.text, topic=spec.topic, difficulty=spec.difficulty,
                     source=spec.source, resume_grounded=spec.resume_grounded, intro=intro)
        db.session.add(q)
        session.active_agent, session.difficulty = agent_key, diff
        json_set(session, "state", state)
        db.session.commit()
        return self._serialize_question(q, q.index, asked + 1, planned, self.total_questions, agent)

    def submit_answer(self, session: InterviewSession, question_id: int, text: str, mode: str = "text", duration: float | None = None,
                      pauses: list[float] | None = None, skipped: bool = False) -> dict:
        if session.status != "active":
            raise AppError("interview_not_active", "This interview is not active.", 409)
        q = db.session.get(Question, question_id)
        if not q or q.session_id != session.id:
            raise AppError("invalid_question", "Question not found in this session.", 404)
        if q.answer is not None:
            raise AppError("already_answered", "This question has already been answered.", 409)
        text = "" if skipped else text
        answer = Answer(question_id=q.id, session_id=session.id, text=text or "[Skipped]" if skipped else text, input_mode=mode if mode in ("text", "voice") else "text",
                        duration_seconds=duration, speech_metrics=speech_metrics(text, duration, pauses))
        db.session.add(answer)
        db.session.flush()
        log_event(log, "answer_received", session_id=session.id, agent=q.agent, words=answer.speech_metrics["word_count"], mode=answer.input_mode)

        result = self.evaluator.evaluate(q.agent, q.text, text, session.role)
        parsed = (session.resume.parsed if session.resume else None) or {}
        chunks = resume_chunks(parsed) + ([" ".join(parsed.get("skills", [])[:25])] if parsed.get("skills") else [])
        if chunks and text:
            best = max(self.embeddings.similarity(text, c) for c in chunks)
            result["resume_alignment"] = _scale_similarity(best, self.embeddings.is_semantic())
        overall = result.pop("overall")
        ev = Evaluation(answer_id=answer.id, scores={k: v for k, v in result.items() if k not in ("feedback", "improvement", "method")} | {"evidence": result.get("evidence", "")},
                        overall=overall, feedback=result["feedback"], improvement=result["improvement"], method=result["method"])
        db.session.add(ev)
        log_event(log, "evaluation_generated", session_id=session.id, agent=q.agent, overall=overall, method=result["method"])

        # Adaptive difficulty
        state = self._state(session)
        history = [h["scores"] | {"overall": h["overall"]} for h in self._agent_history(session, q.agent)]
        skills = [s.lower() for s in parsed.get("skills", [])]
        on_resume = any(s in (q.text + " " + (q.topic or "")).lower() for s in skills)
        current = state["difficulty"].get(q.agent, "MEDIUM")
        d = adaptive.decide(current, q.agent, result | {"overall": overall}, history, on_resume)
        state["difficulty"][q.agent] = d.difficulty
        state["last_action"][q.agent] = d.action
        state["adaptation_log"] = state["adaptation_log"] + [{"question_index": q.index, "agent": q.agent, "from": current, "to": d.difficulty, "action": d.action, "reason": d.reason, "signal": d.signal}]
        json_set(session, "state", state)
        db.session.commit()

        answered = sum(1 for x in session.questions if x.answer)
        return {"answer_id": answer.id, "evaluation": {**result, "overall": overall}, "adaptation": d.to_dict() | {"previous": current},
                "speech_metrics": answer.speech_metrics, "answered": answered, "total_questions": self.total_questions, "has_more": answered < self.total_questions}

    # -------------------------------------------------------------- aggregation
    def items(self, session: InterviewSession) -> list[dict]:
        out = []
        for q in session.questions:
            if not (q.answer and q.answer.evaluation):
                continue
            ev = q.answer.evaluation
            out.append({"index": q.index, "agent": q.agent, "topic": q.topic, "difficulty": q.difficulty, "question": q.text, "answer": q.answer.text,
                        "scores": ev.scores or {}, "overall": ev.overall, "feedback": ev.feedback, "improvement": ev.improvement, "method": ev.method,
                        "resume_alignment": (ev.scores or {}).get("resume_alignment"), "resume_grounded": bool(q.resume_grounded), "source": q.source,
                        "input_mode": q.answer.input_mode, "speech": q.answer.speech_metrics or {}})
        return out

    def duration_seconds(self, session: InterviewSession) -> int:
        if session.duration_seconds is not None:
            return session.duration_seconds
        if session.started_at:
            return int(((session.completed_at or _now()) - session.started_at).total_seconds())
        return 0

    @staticmethod
    def _speech_summary(items: list[dict]) -> dict:
        sp = [i["speech"] for i in items if i.get("speech")]
        wpms = [s["words_per_minute"] for s in sp if s.get("words_per_minute")]
        words = sum(s.get("word_count", 0) for s in sp)
        fill = sum(s.get("filler_count", 0) for s in sp)
        return {"total_words": words, "avg_words_per_answer": round(words / len(sp), 1) if sp else 0, "total_fillers": fill,
                "filler_ratio": round(fill / words, 3) if words else 0, "avg_words_per_minute": round(sum(wpms) / len(wpms)) if wpms else None,
                "voice_answers": sum(1 for i in items if i["input_mode"] == "voice"), "note": "Delivery metrics only; no inference about personality or mental state."}

    def _resume_observations(self, session: InterviewSession, items: list[dict]) -> list[str]:
        if not session.resume:
            return ["No resume was provided, so no resume-based observations are available."]
        p = session.resume.parsed or {}
        obs = [f"Resume sections detected: {', '.join(p.get('sections_found', [])) or 'none'}; {len(p.get('skills', []))} skills identified."]
        grounded = sum(1 for i in items if i["resume_grounded"])
        obs.append(f"{grounded} question(s) were personalised using your resume content.")
        skills = [s.lower() for s in p.get("skills", [])]
        for i in items:
            if i["agent"] == "technical" and i["overall"] < 5 and any(s in (i["question"] + " " + (i["topic"] or "")).lower() for s in skills):
                obs.append(f"A resume-listed skill related to '{(i['topic'] or 'a technical topic').replace('_', ' ')}' was explained only briefly; be ready to discuss listed skills in depth.")
                break
        if not p.get("projects"):
            obs.append("No projects section was detected; adding 2-3 projects with technologies and outcomes makes interviews easier to personalise.")
        return obs

    def dashboard(self, session: InterviewSession) -> dict:
        items = self.items(session)
        scores = compute_scores(items)
        state = self._state(session)
        integrity = summarize_integrity(session.behavior_summary, session.events)
        timeline = [{"index": i["index"], "agent": i["agent"], "score": round(i["overall"] * 10, 1), "difficulty": i["difficulty"], "topic": i["topic"]} for i in items]
        return {
            "session_id": session.id, "status": session.status, "role": session.role, "role_label": role_label(session.role),
            "candidate": {"name": session.user.name, "email": session.user.email}, "date": (session.started_at or session.created_at).isoformat(),
            "duration_seconds": self.duration_seconds(session), "questions_answered": len(items), "total_questions": self.total_questions,
            "scores": scores, "difficulty_progress": [{"index": a["question_index"], "agent": a["agent"], "level": adaptive.LEVELS.index(a["to"]) + 1, "from": a["from"], "to": a["to"], "action": a["action"], "reason": a["reason"]} for a in state["adaptation_log"]],
            "timeline": timeline, "speech_summary": self._speech_summary(items), "integrity": integrity,
            "events": [{"type": e.event_type, "detail": e.detail, "offset_seconds": e.offset_seconds, "duration_seconds": e.duration_seconds} for e in session.events],
            "resume_observations": self._resume_observations(session, items), "questions": items,
            "ai_components": AI_COMPONENTS, "disclaimers": DISCLAIMERS,
        }

    # ------------------------------------------------------------------ complete
    def complete(self, session: InterviewSession) -> dict:
        if session.report:
            return session.report.content
        if session.status == "created":
            raise AppError("interview_not_started", "The interview has not been started yet.", 409)
        session.completed_at = _now()
        session.duration_seconds = self.duration_seconds(session)
        panel = self.sessions.panel_for(session.id)
        data = self.dashboard(session)
        items = data["questions"]
        rl = role_label(session.role)

        reviews = {a: panel.get(a).review(rl, [i for i in items if i["agent"] == a]) for a in ("hr", "technical", "manager")}
        for a in reviews:
            log_event(log, "agent_review_generated", session_id=session.id, agent=a, score=reviews[a]["score"])
        overall = data["scores"]["overall"]
        integ = data["integrity"]
        behav_note = integ["observations"][0] if integ["observations"] else "none"
        panel_out = panel.panel.discuss(rl, reviews, overall, behav_note)

        star_note = [i for i in items if i["agent"] == "manager"]
        recs = {
            "technical_topics": data["scores"]["prep_topics"] or ["No specific weak technical topics were identified; continue practising harder questions."],
            "communication": self._comm_suggestions(data["speech_summary"], data["scores"]["competencies"]),
            "behavioral": [f"Practise the STAR structure; weakest element on average: {min(STAR, key=lambda k: sum(i['scores'].get(k, 0) for i in star_note) / len(star_note)).title()}."] if star_note else ["No manager-round answers were recorded."],
        }
        report = data | {
            "executive_summary": (panel_out["final_assessment"]),
            "readiness": readiness_level(overall), "agent_reviews": reviews, "panel": panel_out, "recommendations": recs,
            "generated_at": _now().isoformat(),
        }
        report["questions"] = items
        db.session.add(FinalReport(session_id=session.id, content=report))
        session.status = "completed"
        report["status"] = "completed"
        db.session.commit()
        self.sessions.release(session.id)
        log_event(log, "interview_completed", session_id=session.id, overall=overall, answered=len(items), duration=session.duration_seconds)
        return report

    @staticmethod
    def _comm_suggestions(sp: dict, comp: dict) -> list[str]:
        out = []
        if sp["filler_ratio"] > 0.04:
            out.append(f"Filler words made up about {round(sp['filler_ratio'] * 100)}% of your words; pause silently instead of using 'um', 'like' or 'actually'.")
        if sp.get("avg_words_per_minute") and sp["avg_words_per_minute"] > 170:
            out.append("Your speaking pace was fast; slow down slightly so key points land.")
        if sp.get("avg_words_per_minute") and sp["avg_words_per_minute"] < 100:
            out.append("Your speaking pace was slow; practise delivering answers more fluently.")
        if sp["avg_words_per_answer"] and sp["avg_words_per_answer"] < 40:
            out.append("Answers were short on average; add an example and a result to each answer.")
        if comp.get("clarity") is not None and comp["clarity"] < 6:
            out.append("Work on clarity: shorter sentences and explicit structure.")
        return out or ["Communication delivery was generally solid; keep practising with timed answers."]
