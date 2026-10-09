import uuid

from agents.hr_agent import HRAgent


class SessionManager:

    def __init__(self):
        self.sessions = {}

    def create_session(self):
        session_id = str(uuid.uuid4())

        self.sessions[session_id] = {
            "status": "active",
            "hr_agent": HRAgent()
        }

        return session_id

    def session_exists(self, session_id):
        return session_id in self.sessions

    def get_hr_agent(self, session_id):
        if session_id not in self.sessions:
            return None

        return self.sessions[session_id]["hr_agent"]

    def end_session(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "completed"