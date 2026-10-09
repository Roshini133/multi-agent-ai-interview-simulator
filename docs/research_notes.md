# Research Notes — Multi-Agent AI Interview Simulator

> No experimental results are reported here. Section 12 lists metrics to measure; none have been measured.

## 1. Problem statement
Candidates lack realistic, personalised, low-cost interview practice. Human mock interviews are scarce and inconsistent; static question banks do not adapt, ignore the candidate's resume, and give little structured feedback on delivery or behaviour.

## 2. Limitations of existing systems
Fixed question lists; single-persona chatbots; feedback limited to text; no multimodal (voice/video) signals; cloud dependence and privacy concerns; opaque scoring; some commercial tools make overreaching claims (emotion, honesty) from facial analysis.

## 3. Proposed system
A local-first platform in which three specialised LLM agents (HR, Technical, Manager) conduct sequential rounds coordinated by an orchestrator, adapt difficulty from evidence-based answer scores, personalise from the resume, observe approximate webcam signals as weak supporting information, and finish with a panel agent that reconciles the three evaluations into a balanced practice assessment and PDF report.

## 4. Architecture
React SPA → Flask REST API → orchestrator → {agents, evaluator, adaptive engine, scoring} → SQLAlchemy DB. Services: Ollama (Llama 3.2 3B), Sentence-Transformers, faster-whisper, MediaPipe/OpenCV. Session state (difficulty per agent, adaptation log, question/answer/evaluation rows) is persisted; agent objects are per-session and rebuilt lazily.

## 5. Methodology (pipeline)
Setup (role, resume) → per-round loop [generate question → answer (voice/text) → evaluate → adapt difficulty] → completion [agent reviews → panel discussion → scoring → report].

## 6. AI components
Pretrained: Llama 3.2 3B; all-MiniLM-L6-v2; MediaPipe FaceLandmarker; faster-whisper. Deterministic: resume parsing, heuristic metrics, event debouncing. Scoring logic: weighted formulas below. Nothing is trained.

## 7. Multi-agent architecture
Agents share a base class (LLM JSON generation, validation, fallback, review). Each has its own prompt, persona, fallback bank and evaluation rubric (HR: communication/professionalism; Technical: accuracy/concept/depth/problem solving; Manager: STAR). **Cross-agent context:** later agents receive short notes from earlier ones (e.g. technical gaps → manager question about learning from gaps). **Panel agent** receives reviews only (not raw answers), must state disagreement when scores differ ≥15 points, and cannot change numeric scores (computed deterministically) — this prevents any single agent from overriding the others.

## 8. Adaptive questioning
Per-agent difficulty ∈ {EASY, MEDIUM, HARD}. Signal = weighted blend of accuracy/depth/concept/relevance/completeness (technical) or overall/relevance/completeness (others). Composite = 0.6·latest + 0.4·mean(last 3). Composite ≥ 8 and relevance ≥ 6 → increase; < 5 (4.5 if the topic is claimed on the resume) → reinforce (easier, related fundamentals); otherwise maintain. Substantive-but-off-topic answers keep the level. The LLM also receives the action (`increase/maintain/reinforce`) and the last turns, so follow-ups are context-aware.

## 9. NLP methodology
Rubric scoring by the LLM in JSON mode (validated, clamped 0–10, malformed output → retry → heuristic fallback). Final metric = 0.7·LLM + 0.3·heuristic (technical correctness metrics 0.85/0.15). Heuristics: length vs. expected, sentence length, filler ratio, hedging/assertive phrases, structure markers, STAR lexical cues, role keyword coverage. Relevance uses embedding cosine similarity between question and answer. Caps: <5 words → ≤3; <15 words → completeness ≤4. Duplicate-question rejection uses embedding similarity > 0.88.

## 10. Resume personalisation
pypdf text extraction → section detection → skill vocabulary + list parsing. Retrieval: query (role + last topic + skills) against resume chunks (projects, internships, experience) via embeddings; top-k snippets are given to the LLM with an instruction to use only those facts. Fallback templates probe projects directly. "Resume relevance" = similarity of the candidate's answers to resume content (consistency), reported separately.

## 11. Computer vision, voice, integrity
- Vision: sparse frames (~1 per 1.5 s), analysed locally. MediaPipe FaceLandmarker → face count, landmark-geometry yaw/pitch (approximate), iris ratio; fallback OpenCV Haar (low quality). Gaze classes: center/left/right/up/down/face_missing/insufficient_data. `screen_attention_ratio` = attentive samples / face-detected samples (approximate).
- Events (debounced): face absent ≥3 s, off-screen ≥4 s, multiple faces, large head movement, tab hidden/blur. Reported as neutral "observed signals" with a disclaimer; excluded from scores.
- Voice: browser speech recognition for live captions; optional faster-whisper server-side (VAD, segment gaps → pauses). Metrics: words, WPM, filler count/ratio, pauses. Delivery only.

## 12. Evaluation methodology & suggested metrics (to be measured)
Answer relevance (correlation with human ratings); semantic similarity (question–answer, resume–question); question-adaptation accuracy (agreement of difficulty changes with human judgement); technical evaluation consistency (score variance on repeated runs, inter-rater agreement with humans, Cohen's/Weighted κ); interview completion rate; resume-question relevance (human-judged); speech transcription accuracy (WER on a test set); face detection accuracy (precision/recall on labelled frames, per backend); system latency (per question, evaluation, report). Ablations: LLM-only vs heuristic vs blended scoring; adaptive vs fixed difficulty; with/without resume retrieval; user studies (usefulness, realism, SUS).

## 13. Responsible AI considerations
Practice framing; no hire/reject; neutral signal wording; no emotion/lie/personality/mental-health inference; behavioural signals excluded from scores; no permanent video storage; PDF parsed in memory; transparent formulas; heuristic-only scores labelled; false-positive risks disclosed (lighting, camera placement, disability, neurodiversity, glasses, cultural gaze norms).

## 14. Limitations
3B-parameter model variance; heuristic scores cannot verify correctness; Haar fallback weak; gaze estimation approximate and camera-dependent; English only; no code execution; no calibration against human raters yet; small fallback question banks.

## 15. Future work
Human-rated calibration set; fine-tuned or larger evaluator; sandboxed coding round; multilingual; accessibility studies; fairness audits across skin tone/lighting/camera setups; company-specific rubrics; longitudinal progress tracking.
