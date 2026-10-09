import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Camera, CameraOff, Eye, LogOut, Mic, MicOff, RotateCcw, SkipForward, Square, Send, Volume2 } from 'lucide-react'
import { api } from '../services/api'
import { useSettings } from '../context/SettingsContext'
import { Brand } from '../components/Layout'
import AgentAvatar from '../components/AgentAvatar'
import VideoPanel from '../components/VideoPanel'
import { ErrorAlert, Loading } from '../components/ui'
import { useMediaStream } from '../hooks/useMediaStream'
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'
import { useAudioRecorder } from '../hooks/useAudioRecorder'
import { useBehaviorMonitor } from '../hooks/useBehaviorMonitor'
import { useTimer } from '../hooks/useTimer'
import { AGENTS, fmtTime, titleCase } from '../utils/format'

export default function InterviewRoom() {
  const { id } = useParams()
  const nav = useNavigate()
  const { settings } = useSettings()
  const videoRef = useRef(null)
  const media = useMediaStream()
  const tts = useSpeechSynthesis(settings.speakQuestions)
  const sr = useSpeechRecognition()
  const recorder = useAudioRecorder(media.stream)

  const [phase, setPhase] = useState('loading') // loading | question | submitting | feedback
  const [q, setQ] = useState(null)
  const [session, setSession] = useState(null)
  const [text, setText] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [error, setError] = useState(null)
  const [voice, setVoice] = useState({ available: false })
  const [meta, setMeta] = useState({ mode: 'text', seconds: 0, pauses: undefined })
  const [transcribing, setTranscribing] = useState(false)
  const [confirmEnd, setConfirmEnd] = useState(false)
  const baseText = useRef('')

  const elapsed = useTimer(session?.duration_seconds ?? 0, !!session)
  const { observation, ratio, events } = useBehaviorMonitor({ sessionId: id, videoRef, enabled: settings.behaviorAnalysis && !!media.stream && phase !== 'loading', cameraOn: media.videoOn })
  const canDictate = sr.supported || voice.available

  const present = useCallback(async (data) => {
    setSession(data.session)
    if (data.finished) { nav(`/interview/${id}/complete`, { replace: true }); return }
    setQ(data.question); setText(''); setFeedback(null); setMeta({ mode: 'text', seconds: 0, pauses: undefined }); sr.reset(); baseText.current = ''
    setPhase('question')
    if (data.question.intro) await tts.speak(data.question.intro)
    await tts.speak(data.question.text)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, nav, tts.speak])

  useEffect(() => {
    let alive = true
    media.start()
    api.voiceStatus().then((v) => alive && setVoice(v)).catch(() => {})
    api.question(id).then((d) => alive && present(d)).catch((e) => alive && setError(e))
    return () => { alive = false }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // Live captions -> editable answer text
  useEffect(() => { if (sr.listening || sr.finalText) setText((baseText.current + ' ' + sr.finalText).trim()) }, [sr.finalText, sr.listening])

  const startAnswer = () => {
    tts.cancel(); setError(null)
    baseText.current = text; sr.reset()
    const a = sr.start(); const b = recorder.start()
    if (!a && !b) setError('Voice capture is not available in this browser. Please type your answer.')
    else setMeta((m) => ({ ...m, mode: 'voice' }))
  }

  const stopAnswer = async () => {
    sr.stop()
    const rec = await recorder.stop()
    if (!rec) return
    setMeta((m) => ({ ...m, seconds: rec.seconds }))
    if (voice.available && rec.blob.size > 1500) {
      setTranscribing(true)
      try {
        const r = await api.transcribe(id, rec.blob)
        if (r.text) { setText(r.text); setMeta((m) => ({ ...m, pauses: r.pauses, seconds: r.speaking_seconds || rec.seconds })) }
      } catch (e) { if (e.code !== 'stt_unavailable') setError(e) } finally { setTranscribing(false) }
    }
  }

  const submit = async (skipped = false) => {
    if (recorder.recording) await stopAnswer()
    setPhase('submitting'); setError(null)
    try {
      const res = await api.answer({ session_id: id, question_id: q.id, answer: text, skipped, input_mode: meta.mode, duration_seconds: meta.seconds || undefined, pauses: meta.pauses })
      setFeedback(res)
      if (settings.showFeedback && res.has_more) setPhase('feedback')
      else if (!res.has_more) nav(`/interview/${id}/complete`)
      else await advance()
    } catch (e) { setError(e); setPhase('question') }
  }

  const advance = async () => {
    setPhase('loading'); setError(null)
    try { await present(await api.next(id)) } catch (e) { setError(e); setPhase('feedback') }
  }

  const endInterview = () => { tts.cancel(); media.stop(); nav(`/interview/${id}/complete`) }

  if (error && !q) return <div className="container page"><ErrorAlert error={error} /><button className="btn btn-primary" style={{ marginTop: 12 }} onClick={() => nav('/dashboard')}>Back to dashboard</button></div>
  if (!q) return <Loading label="Preparing your interviewer..." />

  const agent = AGENTS[q.agent]
  const busy = phase === 'submitting' || phase === 'loading' || transcribing
  const canSubmit = text.trim().length > 0 && !busy && phase === 'question'
  return (
    <div className="room">
      <header className="room-head">
        <Brand />
        <div aria-label="Interview progress">
          <div className="row between small"><b>Question {q.question_number} of {q.total_questions}</b><span className="muted">{agent.label} - {q.stage_number}/{q.stage_total}</span></div>
          <div className="progress" style={{ marginTop: 6 }}><div style={{ width: `${((q.question_number - 1) / q.total_questions) * 100}%` }} /></div>
        </div>
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <span className="badge" aria-label="Elapsed time">{fmtTime(elapsed)}</span>
          <span className="badge good"><span className="dot live" /> Live session</span>
        </div>
      </header>

      <div className="room-body">
        <section className="panel-card interviewer" aria-label="AI interviewer">
          <AgentAvatar agent={q.agent} name={q.agent_name} title={q.agent_title} speaking={tts.speaking} />
          <span className="badge" style={{ alignSelf: 'flex-start' }}>{q.difficulty} | {titleCase(q.topic || 'general')}{q.resume_grounded ? ' | from your resume' : ''}</span>
          {q.intro && <div className="intro-line">{q.intro}</div>}
          <div className="question-box" aria-live="polite" aria-label="Current question">{q.text}</div>
          <div className="row">
            <button className="btn btn-ghost btn-sm" onClick={async () => { await tts.speak(q.text) }} disabled={!tts.supported}><Volume2 size={14} /> Replay question</button>
            {tts.speaking && <button className="btn btn-ghost btn-sm" onClick={tts.cancel}>Stop voice</button>}
          </div>
        </section>

        <section className="panel-card" aria-label="Your camera">
          <VideoPanel ref={videoRef} stream={media.stream} videoOn={media.videoOn}>
            <div className="cam-overlay">
              {recorder.recording && <span className="pill"><span className="rec-dot" /> Recording answer</span>}
              {settings.behaviorAnalysis && observation && <span className="pill"><Eye size={12} /> {observation.label}</span>}
              {settings.behaviorAnalysis && ratio != null && <span className="pill">Attention ~{Math.round(ratio * 100)}%</span>}
            </div>
          </VideoPanel>
          <div className="small muted" style={{ padding: '10px 14px' }}>
            {media.error ? <span style={{ color: 'var(--low)' }}>{media.error} You can continue with text answers.</span>
              : settings.behaviorAnalysis ? <>Approximate observation only ({events} signal{events === 1 ? '' : 's'} noted). Not proof of anything and never affects your score.</> : 'Behavioural observation is off.'}
          </div>
        </section>

        <section className="panel-card answer-panel" aria-label="Your answer">
          <div className="row between"><b>Your answer</b>
            {phase === 'question' && !canDictate && <span className="small muted">Voice input unavailable here - please type.</span>}
            {transcribing && <span className="small muted"><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Transcribing...</span>}</div>
          <textarea className="input" style={{ marginTop: 0 }} rows={5} value={text} onChange={(e) => setText(e.target.value)} disabled={phase !== 'question'} maxLength={4000}
            placeholder={canDictate ? 'Press "Start answering" to speak, or type here. You can edit the transcript before submitting.' : 'Type your answer here...'} aria-label="Answer transcript" />
          {settings.captions && sr.interim && <div className="small muted" aria-live="polite">Hearing: {sr.interim}</div>}
          <ErrorAlert error={error} />
          {phase === 'feedback' && feedback && (
            <div className="feedback" role="status">
              <div className="row between"><b>Quick feedback (practice mode)</b><span className="badge good">{Math.round(feedback.evaluation.overall * 10)}/100</span></div>
              <p style={{ margin: '8px 0' }}>{feedback.evaluation.feedback}</p>
              <p className="small muted" style={{ margin: 0 }}>Tip: {feedback.evaluation.improvement}</p>
              <p className="small muted" style={{ margin: '6px 0 0' }}>Next difficulty: {feedback.adaptation.to || feedback.adaptation.difficulty} ({feedback.adaptation.action})</p>
            </div>)}
        </section>

        <div className="controls">
          <button className={`btn btn-ghost ${!media.audioOn ? 'off' : ''}`} onClick={media.toggleAudio} disabled={!media.stream} aria-pressed={!media.audioOn}>{media.audioOn ? <Mic size={17} /> : <MicOff size={17} />} {media.audioOn ? 'Mute' : 'Unmute'}</button>
          <button className={`btn btn-ghost ${!media.videoOn ? 'off' : ''}`} onClick={media.toggleVideo} disabled={!media.stream} aria-pressed={!media.videoOn}>{media.videoOn ? <Camera size={17} /> : <CameraOff size={17} />} {media.videoOn ? 'Camera on' : 'Camera off'}</button>
          {!media.stream && <button className="btn btn-ghost" onClick={media.start}><RotateCcw size={16} /> Retry camera</button>}
          {phase === 'question' && (recorder.recording || sr.listening
            ? <button className="btn btn-danger solid" onClick={stopAnswer}><Square size={16} /> Stop answering</button>
            : <button className="btn btn-secondary" onClick={startAnswer} disabled={!canDictate || !media.audioOn || busy}><Mic size={16} /> Start answering</button>)}
          {phase === 'feedback'
            ? <button className="btn btn-primary" onClick={advance}>Next question</button>
            : <button className="btn btn-primary" onClick={() => submit(false)} disabled={!canSubmit}><Send size={16} /> Submit answer</button>}
          <button className="btn btn-ghost" onClick={() => submit(true)} disabled={busy || phase !== 'question'}><SkipForward size={16} /> Skip</button>
          {confirmEnd
            ? <span className="row"><span className="small">End now and view results?</span><button className="btn btn-danger solid btn-sm" onClick={endInterview}>Yes, end</button><button className="btn btn-ghost btn-sm" onClick={() => setConfirmEnd(false)}>Cancel</button></span>
            : <button className="btn btn-danger" onClick={() => setConfirmEnd(true)}><LogOut size={16} /> End interview</button>}
        </div>
      </div>
    </div>
  )
}
