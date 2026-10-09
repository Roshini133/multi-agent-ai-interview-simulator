# AI Interview Simulator — *Practice. Perform. Improve.*

**Multi-Agent AI Interview Simulator with Adaptive Questioning, Multimodal Behavioral Analysis and Panel Evaluation**

A full-stack, local-first interview practice platform. A virtual panel (HR, Technical, Manager) interviews you adaptively, personalises questions from your PDF resume, scores answers transparently, observes approximate webcam signals, holds a final panel discussion and produces a dashboard plus a PDF report.

> **Practice tool, not a hiring tool.** Scores are approximate. Webcam/gaze signals are weak, non-conclusive observations and never affect scores. See [Responsible AI](#responsible-ai).

## Architecture

```
frontend/ (React + Vite + Recharts)  ──/api──►  backend/ (Flask)  ──►  Ollama (llama3.2:3b, local)
                                                   │
                                                   ├─ SQLAlchemy → SQLite (dev) / PostgreSQL
                                                   ├─ Sentence-Transformers (optional; lexical fallback)
                                                   ├─ faster-whisper (optional; browser speech fallback)
                                                   └─ MediaPipe FaceLandmarker / OpenCV Haar (local CV)
```

```
backend/
  app.py                    application factory + service wiring
  config.py                 all settings (env / .env)
  agents/                   hr_agent, technical_agent, manager_agent, panel_agent, base_agent
  prompts/                  prompts + fallback question banks per agent
  services/
    interview_orchestrator  state machine: HR → Technical → Manager → Panel → Report
    session_manager         per-session agent instances (no shared global agents)
    ollama_service          retries, timeouts, JSON extraction/validation
    answer_evaluator        LLM rubric + deterministic heuristics, blended and capped
    adaptive_questioning    difficulty engine (EASY/MEDIUM/HARD)
    scoring_service         transparent category/overall scoring
    resume_parser           pypdf + section/skill extraction
    embedding_service       semantic similarity (resume retrieval, relevance)
    voice_service           faster-whisper + speech metrics
    face_analysis / gaze_analysis / behavioral_analysis   local CV → summarised events
    report_service          ReportLab PDF
  models/ database/ routes/ utils/ tests/
frontend/src/  pages/ components/ hooks/ services/ context/ utils/ styles/
legacy_prototype/           your original files, kept for reference
```

**Which parts are what** (also documented in `docs/research_notes.md`):

| Kind | Components |
|---|---|
| Pretrained models | Llama 3.2 3B (Ollama), all-MiniLM-L6-v2 (Sentence-Transformers), MediaPipe FaceLandmarker, faster-whisper |
| Classic CV | OpenCV Haar cascades (fallback face detection) |
| Deterministic algorithms | resume section/skill extraction, heuristic answer metrics (length, structure, fillers, STAR cues), behavioural event debouncing |
| Scoring logic | per-answer weighted scores, adaptive difficulty engine, category-weighted overall score |

No custom model is trained.

## Run locally

Prerequisites: Python 3.11+, Node 18+, [Ollama](https://ollama.com).

**1. Ollama**
```bash
# install from https://ollama.com/download, then:
ollama pull llama3.2:3b
ollama serve            # skip if the Ollama app/service is already running
```

**2. Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows      (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Linux/macOS: cp .env.example .env   → set SECRET_KEY
python app.py                    # http://127.0.0.1:5000
```

**3. Frontend**
```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173  (proxies /api to :5000)
```
Open http://localhost:5173, register, and start an interview. Use `localhost` — browsers only allow camera/mic on `localhost` or HTTPS.

### Optional components
```bash
pip install -r requirements-optional.txt     # sentence-transformers + faster-whisper (large downloads)
# in backend/.env:  EMBEDDINGS_ENABLED=true   WHISPER_ENABLED=true   WHISPER_MODEL=base.en
```
Better face/gaze quality — download the MediaPipe model once:
```bash
curl -L -o backend/data/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```
Without it the app uses OpenCV Haar cascades (`quality: low`). Check **Settings → System status** to see what is active.

The app works without Ollama (built-in question banks + heuristic scoring, clearly labelled "heuristic"), so you can always demo the full flow; with Ollama, questions and scoring are LLM-driven.

## Run with Docker
```bash
cp .env.example .env             # set SECRET_KEY
docker compose up --build        # UI: http://localhost:3000
```
Ollama runs **on the host** (not in compose, so the model is downloaded once and never re-pulled on container start). The backend reaches it via `OLLAMA_BASE_URL=http://host.docker.internal:11434` (`extra_hosts` makes this work on Linux too). Make sure Ollama is listening on an address reachable from Docker (on Linux: `OLLAMA_HOST=0.0.0.0 ollama serve`).
PostgreSQL (optional): `docker compose --profile postgres up --build` and set `DATABASE_URL=postgresql+psycopg2://interview:interview@postgres:5432/interview`.
Optional heavy models in the image: `INSTALL_OPTIONAL=true docker compose build` (model files are cached in the `model-cache` volume).

## Environment variables (backend)

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | random per start | signs auth tokens — **set it** |
| `DATABASE_URL` | `sqlite:///data/interview.db` | SQLite or `postgresql+psycopg2://…` |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | `http://localhost:11434` / `llama3.2:3b` | LLM endpoint/model |
| `OLLAMA_TIMEOUT` / `OLLAMA_RETRIES` | 90 / 2 | LLM robustness |
| `LLM_ENABLED` | true | false = deterministic fallback only |
| `CORS_ORIGINS` | localhost:5173,3000 | allowed origins |
| `HR_QUESTIONS` / `TECHNICAL_QUESTIONS` / `MANAGER_QUESTIONS` | 4 / 5 / 3 | interview length |
| `EMBEDDINGS_ENABLED`, `EMBEDDING_MODEL` | true, all-MiniLM-L6-v2 | needs sentence-transformers |
| `WHISPER_ENABLED`, `WHISPER_MODEL` | false, base.en | needs faster-whisper |
| `VISION_ENABLED`, `MEDIAPIPE_FACE_MODEL` | true, `data/face_landmarker.task` | webcam analysis |
| `FACE_ABSENT_SECONDS`, `OFF_SCREEN_SECONDS` | 3, 4 | event thresholds |
| `MAX_RESUME_MB`, `MAX_AUDIO_MB`, `MAX_FRAME_KB` | 5, 8, 600 | upload limits |

## Testing
```bash
cd backend && pytest -q          # 40 tests, no LLM/network required (Ollama is stubbed/unavailable)
cd frontend && npm run build
```
Covered: session creation/invalid/isolation, HR/Technical question generation, resume personalisation, answer evaluation (LLM stub, malformed LLM, heuristic caps, STAR), adaptive difficulty, resume parsing/upload validation, full 12-question flow, early completion, report + PDF generation, behaviour event logic, voice metrics, error responses.

## API (all JSON: `{success, data}` / `{success:false, error:{code,message}}`)
`POST /api/auth/register|login`, `GET /api/auth/me` · `GET /api/interview/roles` · `POST /api/interview/start` · `POST /api/interview/question` · `POST /api/interview/answer` (stores + evaluates) · `POST /api/interview/evaluate` · `POST /api/interview/next` · `GET /api/interview/{id}` · `POST /api/interview/{id}/complete` · `POST /api/resume/upload` · `POST /api/voice/transcribe` · `POST /api/behavior/analyze` (one frame) · `POST /api/behavior/event` · `GET /api/dashboard/{id}` · `GET /api/report/{id}` · `GET /api/report/{id}/pdf` · `GET /api/system/status`

## Responsible AI
- Gaze/head direction is **not** proof of cheating; it can be wrong (camera angle, lighting, glasses, thinking). Signals use neutral wording ("Repeated off-screen gaze detected") and are **excluded from all scores**.
- No lie detection, no emotion/personality/mental-health inference, no protected-attribute inference. Voice metrics are delivery-only (pace, fillers, pauses).
- Video frames are analysed in memory, one small frame every ~1.5 s, and never written to disk or sent to the LLM; only counters and debounced events are stored.
- Scores are approximate practice feedback. Heuristic-only scores are labelled; the LLM is instructed to score only what was said and never invent experience; very short answers are capped.
- Uploaded PDFs are parsed in memory; only extracted text is stored.

## Known limitations (honest list)
- **Not verified in the build environment:** the Docker images/compose stack (no Docker available there — the compose file is syntax-checked only), a live Ollama run, Whisper transcription, the Sentence-Transformers path, the MediaPipe landmarker path, and the browser UI end-to-end (the frontend compiles; camera/mic flows need a real browser). The LLM code path was tested with a stub, the fallback path with the real server over HTTP.
- OpenCV Haar fallback is crude: face detection was checked on a sample photo, but multi-face and head-turn detection is weak. Use the MediaPipe model for better results.
- Heuristic scoring (used without Ollama) cannot judge technical correctness; technical scores are capped at ~6/10 in that mode.
- Llama 3.2 3B can be inconsistent as a scorer; scores are blended with heuristics and clamped, but expect noise.
- No code-execution editor (running arbitrary candidate code safely needs sandboxing); answers are text/voice.
- Sessions' agent objects and the behaviour tracker live in process memory (run one gunicorn worker, as the Dockerfile does); interview data itself is in the DB so restarts are safe. Schema is created with `create_all`; use Alembic for migrations in production. No rate limiting.
- Web Speech API captions work best in Chrome/Edge.

## Future work
Code editor with sandboxed execution, Alembic migrations, rate limiting, streaming LLM responses, multi-language interviews, calibrated evaluation against human-rated answers, custom question banks per company.
