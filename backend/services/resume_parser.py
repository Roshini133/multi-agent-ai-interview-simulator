"""PDF resume parsing (pypdf) + rule-based section extraction. Nothing is written to disk."""
from __future__ import annotations

import io
import re

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from utils.errors import AppError

SECTION_ALIASES = {
    "education": ["education", "academic background", "academics", "qualifications"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "tech stack"],
    "projects": ["projects", "academic projects", "personal projects", "key projects"],
    "internships": ["internships", "internship", "internship experience"],
    "certifications": ["certifications", "certificates", "licenses", "courses"],
    "experience": ["experience", "work experience", "professional experience", "employment", "employment history"],
    "achievements": ["achievements", "awards", "accomplishments", "honors", "honours", "publications", "extracurricular"],
    "summary": ["summary", "objective", "profile", "about me", "career objective"],
}
HEADING_LOOKUP = {alias: key for key, aliases in SECTION_ALIASES.items() for alias in aliases}

SKILL_VOCAB = [
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "rust", "kotlin", "swift", "php", "ruby", "sql", "r", "matlab", "bash",
    "react", "angular", "vue", "next.js", "node.js", "express", "flask", "django", "fastapi", "spring", "spring boot", "hibernate", "html", "css", "tailwind", "bootstrap",
    "mysql", "postgresql", "mongodb", "sqlite", "redis", "oracle", "firebase", "docker", "kubernetes", "git", "github", "jenkins", "aws", "azure", "gcp", "linux",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "pandas", "numpy", "matplotlib", "opencv", "mediapipe", "nlp", "transformers", "hugging face", "langchain",
    "cnn", "lstm", "bi-lstm", "rnn", "gan", "yolo", "bert", "llm", "machine learning", "deep learning", "computer vision", "data analysis", "data visualization",
    "power bi", "tableau", "excel", "rest api", "graphql", "microservices", "junit", "pytest", "selenium", "jira", "agile", "scrum", "dsa", "oop", "dbms", "operating systems",
]

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{8,}\d")


def extract_text(data: bytes, max_pages: int = 8, max_chars: int = 30000) -> str:
    """Extract text from PDF bytes; raise a clean AppError on failure."""
    if not data.startswith(b"%PDF"):
        raise AppError("invalid_file", "The uploaded file is not a valid PDF.", 400)
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise AppError("resume_encrypted", "Password-protected PDFs are not supported.", 422)
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:max_pages])
    except AppError:
        raise
    except (PyPdfError, ValueError, KeyError, OSError, RecursionError):
        raise AppError("resume_parse_failed", "We could not read this PDF. Please upload a text-based (not scanned) resume.", 422)
    text = text.strip()
    if len(text) < 40:
        raise AppError("resume_empty", "No readable text was found. Scanned/image-only resumes are not supported.", 422)
    return text[:max_chars]


def _heading_key(line: str) -> str | None:
    cleaned = re.sub(r"[^a-z &/]", "", line.lower()).strip()
    if 0 < len(cleaned) <= 35:
        return HEADING_LOOKUP.get(cleaned)
    return None


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"_header": []}
    current = "_header"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key = _heading_key(line)
        if key:
            current = key
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _guess_name(header_lines: list[str]) -> str | None:
    for line in header_lines[:6]:
        if EMAIL_RE.search(line) or PHONE_RE.search(line) or any(ch.isdigit() for ch in line):
            continue
        words = line.replace(",", " ").split()
        if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z.'-]+", w) for w in words):
            return line.title() if line.isupper() else line
    return None


def _bullets(lines: list[str], limit: int = 12) -> list[str]:
    """Merge wrapped lines into items: a new item starts at a bullet or a Title-like line."""
    items: list[str] = []
    for line in lines:
        starts_new = bool(re.match(r"^[•\-\u2022\*▪●◦]\s*", line)) or not items or (line[:1].isupper() and len(items[-1]) > 60 and items[-1].endswith((".", ")")))
        clean = re.sub(r"^[•\-\u2022\*▪●◦]\s*", "", line)
        if starts_new:
            items.append(clean)
        else:
            items[-1] += " " + clean
    return [i[:300] for i in items[:limit]]


def _extract_skills(text: str, skills_section: list[str]) -> list[str]:
    found: list[str] = []
    lowered = " " + re.sub(r"[\n,;/|]", " ", text.lower()) + " "
    for skill in SKILL_VOCAB:
        pattern = r"(?<![a-z0-9+#])" + re.escape(skill) + r"(?![a-z0-9+#])"
        if re.search(pattern, lowered):
            found.append(skill)
    for line in skills_section:  # also capture skills not in the vocabulary (comma-separated lists)
        for part in re.split(r"[,;|•]", line.split(":", 1)[-1]):
            part = part.strip()
            if 1 < len(part) <= 30 and part.lower() not in found and not part.lower().startswith(("and ", "familiar")):
                found.append(part)
    seen, out = set(), []
    for s in found:
        if s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out[:40]


def parse_resume(text: str) -> dict:
    """Structured resume data. Deterministic (no LLM), so it is fast and testable."""
    sections = _split_sections(text)
    email = EMAIL_RE.search(text)
    parsed = {
        "name": _guess_name(sections.get("_header", [])),
        "email": email.group(0) if email else None,
        "summary": " ".join(sections.get("summary", []))[:500] or None,
        "education": _bullets(sections.get("education", []), 6),
        "skills": _extract_skills(text, sections.get("skills", [])),
        "projects": _bullets(sections.get("projects", []), 8),
        "internships": _bullets(sections.get("internships", []), 6),
        "certifications": _bullets(sections.get("certifications", []), 8),
        "experience": _bullets(sections.get("experience", []), 8),
        "achievements": _bullets(sections.get("achievements", []), 8),
    }
    parsed["sections_found"] = [k for k in ("education", "skills", "projects", "internships", "certifications", "experience", "achievements") if parsed[k]]
    return parsed


def resume_chunks(parsed: dict) -> list[str]:
    """Retrievable snippets (projects, internships, experience...) for semantic matching."""
    chunks: list[str] = []
    for key in ("projects", "internships", "experience", "achievements", "certifications"):
        chunks.extend(parsed.get(key) or [])
    return chunks
