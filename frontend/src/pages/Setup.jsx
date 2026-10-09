import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Briefcase, Brain, Code2, Coffee, Database, Layers } from 'lucide-react'
import { api } from '../services/api'
import { ErrorAlert, Stepper } from '../components/ui'

export const STEPS = ['Role', 'Resume', 'Device check', 'Interview']
const ICONS = { java_developer: Coffee, python_developer: Code2, full_stack_developer: Layers, ai_ml_engineer: Brain, data_analyst: Database, software_engineer: Briefcase }

export default function Setup() {
  const [roles, setRoles] = useState([])
  const [role, setRole] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()
  useEffect(() => { api.roles().then((d) => setRoles(d.roles)).catch(setError) }, [])

  const go = async () => {
    setBusy(true); setError(null)
    try { const s = await api.startInterview(role); nav(`/interview/${s.session_id}/resume`) } catch (e) { setError(e); setBusy(false) }
  }
  return (
    <div className="container page" style={{ maxWidth: 860 }}>
      <Stepper steps={STEPS} current={0} />
      <h1 style={{ fontSize: '1.7rem' }}>Which role are you interviewing for?</h1>
      <p className="muted">The technical round is tailored to this role. The interview has an HR, a Technical and a Manager round (about 12 questions).</p>
      <ErrorAlert error={error} />
      <div className="grid g3" style={{ margin: '18px 0' }} role="radiogroup" aria-label="Job role">
        {roles.map((r) => { const Icon = ICONS[r.key] || Briefcase; return (
          <button key={r.key} role="radio" aria-checked={role === r.key} className={`role-card ${role === r.key ? 'selected' : ''}`} onClick={() => setRole(r.key)}>
            <Icon size={24} color="#1565C0" /><b>{r.label}</b>
          </button>) })}
      </div>
      <button className="btn btn-primary btn-lg" disabled={!role || busy} onClick={go}>{busy ? 'Creating session...' : 'Continue'}</button>
    </div>
  )
}
