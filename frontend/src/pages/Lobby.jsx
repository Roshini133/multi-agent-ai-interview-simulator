import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Clock, Eye, ListChecks, Mic, ShieldCheck } from 'lucide-react'
import { api } from '../services/api'
import { useSettings } from '../context/SettingsContext'
import { ErrorAlert, Loading, Stepper } from '../components/ui'
import { STEPS } from './Setup'
import { AGENTS } from '../utils/format'

export default function Lobby() {
  const { id } = useParams()
  const nav = useNavigate()
  const { settings, update } = useSettings()
  const [session, setSession] = useState(null)
  const [error, setError] = useState(null)
  const [agree, setAgree] = useState(false)

  useEffect(() => {
    api.session(id).then((s) => { if (s.status === 'completed') nav(`/results/${id}`, { replace: true }); else setSession(s) }).catch(setError)
  }, [id, nav])
  if (!session && !error) return <Loading />
  if (!session) return <div className="container page"><ErrorAlert error={error} /></div>

  return (
    <div className="container page" style={{ maxWidth: 860 }}>
      <Stepper steps={STEPS} current={3} />
      <h1 style={{ fontSize: '1.7rem' }}>Interview lobby - {session.role_label}</h1>
      <p className="muted">You will meet three interviewers in turn. Answer as you would in a real interview.</p>
      <div className="grid g3" style={{ margin: '16px 0' }}>
        {session.plan.map((p) => (<div className="card" key={p.agent}><span className="badge">{AGENTS[p.agent].label}</span><h3 style={{ marginTop: 10 }}>{p.count} questions</h3><p className="muted small" style={{ margin: 0 }}>{{ hr: 'Communication, motivation and culture fit.', technical: 'Role-specific and adaptive to your answers.', manager: 'Behavioural questions - use the STAR method.' }[p.agent]}</p></div>))}
      </div>
      <div className="card stack">
        <h3>Before you begin</h3>
        <div className="row"><ListChecks size={18} /><span>Answers can be spoken (live captions) or typed. You can edit the transcript before submitting.</span></div>
        <div className="row"><Clock size={18} /><span>Expect about 20-30 minutes. You can end early to see partial results.</span></div>
        <div className="row"><Mic size={18} /><span>The interviewer reads questions aloud; you can turn this off in Settings.</span></div>
        <div className="row"><Eye size={18} /><span>Optional webcam observation: approximate face/head-direction signals are computed on the server from one small frame every ~1.5 s and immediately discarded.</span></div>
        <label className="row" style={{ cursor: 'pointer' }}><input type="checkbox" checked={settings.behaviorAnalysis} onChange={(e) => update({ behaviorAnalysis: e.target.checked })} /> Enable webcam behavioural observations</label>
        <div className="alert info"><ShieldCheck size={18} style={{ flexShrink: 0 }} /><div>These signals are approximate, may be wrong, are <b>not</b> proof of cheating, and never change your score. This is a practice assessment, not an employment decision.</div></div>
        <label className="row" style={{ cursor: 'pointer' }}><input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} /> I understand and I'm ready to begin.</label>
        <div><button className="btn btn-primary btn-lg" disabled={!agree} onClick={() => nav(`/interview/${id}/room`)}>{session.status === 'active' ? 'Resume interview' : 'Start interview'}</button></div>
      </div>
    </div>
  )
}
