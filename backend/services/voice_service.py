"""Speech-to-text (faster-whisper, optional) and simple, non-diagnostic speech metrics."""
from __future__ import annotations

import logging
import os
import re
import tempfile

log = logging.getLogger(__name__)

FILLER_PATTERNS = [r"\bum+\b", r"\buh+\b", r"\berm?\b", r"\blike\b", r"\bactually\b", r"\bbasically\b", r"\byou know\b", r"\bi mean\b", r"\bsort of\b", r"\bkind of\b"]


class VoiceUnavailable(Exception):
    pass


def count_fillers(text: str) -> dict[str, int]:
    lowered = (text or "").lower()
    counts = {}
    for pat in FILLER_PATTERNS:
        n = len(re.findall(pat, lowered))
        if n:
            counts[pat.replace(r"\b", "").replace("+", "").replace("?", "")] = n
    return counts


def speech_metrics(text: str, duration_seconds: float | None = None, pauses: list[float] | None = None) -> dict:
    """Word count, WPM, fillers and pauses. These describe delivery only - nothing psychological."""
    words = re.findall(r"[A-Za-z0-9'’+#-]+", text or "")
    fillers = count_fillers(text)
    total_fillers = sum(fillers.values())
    metrics: dict = {
        "word_count": len(words),
        "filler_count": total_fillers,
        "filler_ratio": round(total_fillers / len(words), 3) if words else 0.0,
        "fillers": fillers,
        "speaking_duration_seconds": round(duration_seconds, 1) if duration_seconds else None,
        "words_per_minute": None,
        "pause_count": None,
        "longest_pause_seconds": None,
    }
    if duration_seconds and duration_seconds >= 3 and words:
        metrics["words_per_minute"] = round(len(words) / (duration_seconds / 60.0))
    if pauses is not None:
        significant = [p for p in pauses if p >= 1.0]
        metrics["pause_count"] = len(significant)
        metrics["longest_pause_seconds"] = round(max(significant), 1) if significant else 0.0
    return metrics


class VoiceService:
    def __init__(self, enabled: bool, model_name: str = "base.en", compute_type: str = "int8"):
        self.enabled, self.model_name, self.compute_type = enabled, model_name, compute_type
        self._model = None
        self._error: str | None = None

    def status(self) -> dict:
        if not self.enabled:
            return {"available": False, "reason": "Server-side transcription is disabled (WHISPER_ENABLED=false). Browser speech recognition or text input will be used."}
        if self._model is None and self._error is None:
            try:
                self._load()
            except VoiceUnavailable:
                pass
        return {"available": self._model is not None, "model": self.model_name, "reason": self._error}

    def _load(self):
        if self._model is not None:
            return self._model
        if not self.enabled:
            raise VoiceUnavailable("disabled")
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_name, device="cpu", compute_type=self.compute_type)
            self._error = None
        except Exception as e:  # noqa: BLE001
            self._error = "faster-whisper is not installed or the model could not be loaded."
            log.warning("whisper_unavailable: %s", type(e).__name__)
            raise VoiceUnavailable(self._error)
        return self._model

    def transcribe(self, audio: bytes, suffix: str = ".webm") -> dict:
        model = self._load()
        fd, path = tempfile.mkstemp(suffix=suffix)  # temporary only; removed immediately after decoding
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(audio)
            segments, info = model.transcribe(path, vad_filter=True, beam_size=1)
            segs = list(segments)
        except Exception as e:  # noqa: BLE001
            log.warning("transcription_failed: %s", type(e).__name__)
            raise VoiceUnavailable("Transcription failed for this recording.")
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
        text = " ".join(s.text.strip() for s in segs).strip()
        pauses = [max(0.0, segs[i + 1].start - segs[i].end) for i in range(len(segs) - 1)]
        speaking = sum(max(0.0, s.end - s.start) for s in segs)
        return {"text": text, "language": getattr(info, "language", None), "speaking_seconds": speaking,
                "pauses": pauses, "segments": [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]}
