"""Per-session agent registry.

Each interview session owns its own HR / Technical / Manager / Panel agent instances (no globals shared
between candidates). Instances are lazily (re)built, so a server restart does not break active sessions -
the durable interview state lives in the database.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from agents.hr_agent import HRAgent
from agents.manager_agent import ManagerAgent
from agents.panel_agent import PanelAgent
from agents.technical_agent import TechnicalAgent
from services.embedding_service import EmbeddingService
from services.ollama_service import OllamaService

log = logging.getLogger(__name__)


@dataclass
class AgentPanel:
    hr: HRAgent
    technical: TechnicalAgent
    manager: ManagerAgent
    panel: PanelAgent

    def get(self, key: str):
        return {"hr": self.hr, "technical": self.technical, "manager": self.manager}[key]


class SessionManager:
    def __init__(self, llm: OllamaService, embeddings: EmbeddingService):
        self.llm, self.embeddings = llm, embeddings
        self._panels: dict[str, AgentPanel] = {}
        self._lock = threading.Lock()

    def panel_for(self, session_id: str) -> AgentPanel:
        with self._lock:
            if session_id not in self._panels:
                self._panels[session_id] = AgentPanel(
                    HRAgent(session_id, self.llm, self.embeddings), TechnicalAgent(session_id, self.llm, self.embeddings),
                    ManagerAgent(session_id, self.llm, self.embeddings), PanelAgent(self.llm))
            return self._panels[session_id]

    def release(self, session_id: str) -> None:
        with self._lock:
            self._panels.pop(session_id, None)

    def active_count(self) -> int:
        return len(self._panels)
