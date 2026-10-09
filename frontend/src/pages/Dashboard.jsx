import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Plus } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { ErrorAlert, Kpi, Loading, ScoreBadge } from '../components/ui'
import { fmtDate, fmtTime } from '../utils/format'

const nextRoute = (s) => (s.status === 'completed' ? `/results/${s.session_id}` : s.status === 'created' ? `/interview/${s.session_id}/resume` : `/interview/${s.session_id}/lobby`)

export default function Dashboard() {
  const { user } = useAuth()
  const [sessions, setSessions] = useState(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const nav = useNavigate()

  useEffect(() => {
    api.sessions().then((d) => setSessions(d.sessions)).catch(setError)
    api.status().then(setStatus).catch(() => {})
  }, [])

  if (!sessions && !error) return <Loading />
  const done = (sessions || []).filter((s) => s.status === 'completed')
  const avg = done.length ? done.reduce((a, s) => a + (s.overall_score || 0), 0) / done.length : null
  const best = done.length ? Math.max(...done.map((s) => s.overall_score || 0)) : null

  return (
    <div className="container page">
      <div className="row between wrap" style={{ marginBottom: 20 }}>
        <div><h1 style={{ fontSize: '1.7rem' }}>Hello, {user.name.split(' ')[0]}</h1><p className="muted">Track your interview practice and pick up where you left off.</p></div>
        <Link to="/setup" className="btn btn-primary"><Plus size={17} /> New interview</Link>
      </div>
      <ErrorAlert error={error} />
      {status && !status.llm.available && <div style={{ marginBottom: 16 }}><ErrorAlert kind="warn" error={`AI model offline: ${status.llm.reason || 'Ollama unavailable'}. Interviews still work with built-in question banks and heuristic scoring (less personalised).`} /></div>}
      <div className="grid g3" style={{ marginBottom: 20 }}>
        <Kpi label="Interviews completed" value={done.length} />
        <Kpi label="Average score" value={avg == null ? '-' : Math.round(avg)} sub="out of 100" />
        <Kpi label="Best score" value={best == null ? '-' : Math.round(best)} sub="out of 100" />
      </div>
      <div className="card">
        <h3>Your interviews</h3>
        {!sessions?.length ? <p className="muted">No interviews yet. Start your first practice interview.</p> : (
          <div style={{ overflowX: 'auto' }}><table className="tbl">
            <thead><tr><th>Role</th><th>Date</th><th>Status</th><th>Duration</th><th>Score</th><th /></tr></thead>
            <tbody>{sessions.map((s) => (
              <tr key={s.session_id}>
                <td><b>{s.role_label}</b></td><td>{fmtDate(s.created_at)}</td>
                <td><span className={`badge ${s.status === 'completed' ? 'good' : 'ok'}`}>{s.status === 'created' ? 'not started' : s.status}</span></td>
                <td>{s.duration_seconds ? fmtTime(s.duration_seconds) : '-'}</td>
                <td>{s.status === 'completed' ? <ScoreBadge value={s.overall_score} /> : `${s.questions_answered}/${s.total_questions} answered`}</td>
                <td><button className="btn btn-ghost btn-sm" onClick={() => nav(nextRoute(s))}>{s.status === 'completed' ? 'View results' : 'Continue'} <ArrowRight size={14} /></button></td>
              </tr>))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  )
}
