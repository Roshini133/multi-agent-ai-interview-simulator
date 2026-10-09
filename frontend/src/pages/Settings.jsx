import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { useSettings } from '../context/SettingsContext'
import { useAuth } from '../context/AuthContext'

const Toggle = ({ label, hint, k }) => {
  const { settings, update } = useSettings()
  return (
    <label className="row between" style={{ padding: '12px 0', borderBottom: '1px solid #EEF0F3', cursor: 'pointer' }}>
      <span><b>{label}</b><br /><span className="muted small">{hint}</span></span>
      <input type="checkbox" role="switch" checked={settings[k]} onChange={(e) => update({ [k]: e.target.checked })} style={{ width: 20, height: 20 }} />
    </label>
  )
}
const St = ({ label, ok, detail }) => <tr><td>{label}</td><td><span className={`badge ${ok ? 'good' : 'ok'}`}>{ok ? 'Available' : 'Fallback'}</span></td><td className="small muted">{detail}</td></tr>

export default function Settings() {
  const { user } = useAuth()
  const { reset } = useSettings()
  const [s, setS] = useState(null)
  useEffect(() => { api.status().then(setS).catch(() => {}) }, [])
  return (
    <div className="container page" style={{ maxWidth: 820 }}>
      <h1 style={{ fontSize: '1.7rem' }}>Settings</h1>
      <div className="card" style={{ marginBottom: 16 }}>
        <h3>Interview preferences</h3>
        <Toggle k="speakQuestions" label="Read questions aloud" hint="The AI interviewer speaks using your browser's voice." />
        <Toggle k="captions" label="Live captions" hint="Show what the browser hears while you speak." />
        <Toggle k="showFeedback" label="Quick feedback after each answer" hint="Turn off for a realistic, no-feedback experience." />
        <Toggle k="behaviorAnalysis" label="Webcam behavioural observations" hint="Approximate face/head-direction signals. Frames are processed in memory and not stored." />
        <button className="btn btn-ghost btn-sm" style={{ marginTop: 12 }} onClick={reset}>Restore defaults</button>
      </div>
      <div className="card" style={{ marginBottom: 16 }}>
        <h3>System status</h3>
        {!s ? <p className="muted">Checking...</p> : (
          <table className="tbl"><tbody>
            <St label="Local LLM (Ollama)" ok={s.llm.available} detail={s.llm.available ? s.llm.model : s.llm.reason} />
            <St label="Semantic embeddings" ok={s.embeddings.available} detail={s.embeddings.backend} />
            <St label="Speech-to-text (Whisper)" ok={s.speech_to_text.available} detail={s.speech_to_text.available ? s.speech_to_text.model : 'Using browser speech recognition or text'} />
            <St label="Face / gaze analysis" ok={s.vision.backend?.startsWith('mediapipe')} detail={`${s.vision.backend} (quality: ${s.vision.quality})`} />
          </tbody></table>)}
      </div>
      <div className="card"><h3>Account</h3><p style={{ margin: 0 }}>{user.name} - {user.email}</p></div>
      <div className="card" style={{ marginTop: 16 }}><h3>Responsible AI</h3>
        <ul className="bul small"><li>Results are interview practice feedback, not hiring decisions.</li><li>Gaze and head-pose signals are approximate and can be wrong; they are not proof of cheating or dishonesty.</li>
          <li>Facial expressions are not used to judge honesty, personality or mental health.</li><li>Behavioural signals never change your score.</li></ul></div>
    </div>
  )
}
