import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { api } from '../services/api'
import { ErrorAlert } from '../components/ui'

const STEPS = ['HR interviewer is reviewing your answers', 'Technical interviewer is reviewing your answers', 'Hiring manager is reviewing your answers', 'The panel is discussing and combining evaluations', 'Building your report']

export default function Completion() {
  const { id } = useParams()
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const started = useRef(false)

  const run = useCallback(async () => {
    setError(null)
    try { setResult(await api.complete(id)) } catch (e) { setError(e) }
  }, [id])

  useEffect(() => { if (!started.current) { started.current = true; run() } }, [run])
  useEffect(() => {
    if (result || error) return undefined
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 4000)
    return () => clearInterval(t)
  }, [result, error])

  return (
    <div className="container page" style={{ maxWidth: 640 }}>
      <div className="card center" style={{ padding: 36 }}>
        {result ? (
          <>
            <CheckCircle2 size={52} color="#1B7F4B" />
            <h1 style={{ fontSize: '1.6rem', marginTop: 10 }}>Interview complete</h1>
            <p className="muted">Practice level: <b>{result.readiness}</b>. Your dashboard and PDF report are ready.</p>
            <div className="row wrap" style={{ justifyContent: 'center' }}>
              <button className="btn btn-primary btn-lg" onClick={() => nav(`/results/${id}`)}>View performance dashboard</button>
              <button className="btn btn-secondary btn-lg" onClick={() => nav(`/report/${id}`)}>Detailed report</button>
            </div>
          </>
        ) : error ? (
          <>
            <ErrorAlert error={error} />
            <div className="row" style={{ justifyContent: 'center', marginTop: 16 }}>
              {error.code !== 'interview_not_started' && <button className="btn btn-primary" onClick={run}>Try again</button>}
              <button className="btn btn-ghost" onClick={() => nav('/dashboard')}>Back to dashboard</button>
            </div>
          </>
        ) : (
          <>
            <span className="spinner" style={{ width: 40, height: 40 }} />
            <h2 style={{ marginTop: 16 }}>Wrapping up your interview</h2>
            <p className="muted" role="status">{STEPS[step]}...</p>
            <p className="muted small">With a local AI model this can take a minute.</p>
          </>
        )}
      </div>
    </div>
  )
}
