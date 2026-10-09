import { AlertTriangle, Info } from 'lucide-react'
import { scoreTone } from '../utils/format'

export const ErrorAlert = ({ error, kind = 'error' }) => error ? (
  <div className={`alert ${kind}`} role="alert"><AlertTriangle size={18} style={{ flexShrink: 0, marginTop: 2 }} /><div>{typeof error === 'string' ? error : error.message}</div></div>
) : null

export const InfoAlert = ({ children }) => <div className="alert info"><Info size={18} style={{ flexShrink: 0, marginTop: 2 }} /><div>{children}</div></div>

export const Loading = ({ label = 'Loading...' }) => <div className="center muted" style={{ padding: 60 }}><span className="spinner" /> <div style={{ marginTop: 10 }}>{label}</div></div>

export function Stepper({ steps, current }) {
  return (
    <ol className="stepper" aria-label="Progress" style={{ listStyle: 'none', padding: 0 }}>
      {steps.map((s, i) => (
        <li key={s} className={`step ${i < current ? 'done' : i === current ? 'current' : ''}`} aria-current={i === current ? 'step' : undefined}>
          <span className="n">{i < current ? '\u2713' : i + 1}</span>{s}
        </li>
      ))}
    </ol>
  )
}

export function ScoreRing({ value, size = 120, label }) {
  const v = value == null ? 0 : Math.max(0, Math.min(100, value))
  const r = size / 2 - 9, c = 2 * Math.PI * r
  const color = { good: '#1B7F4B', ok: '#1565C0', low: '#C0392B', muted: '#97A0AF' }[scoreTone(value)]
  return (
    <div className="score-ring" style={{ width: size, height: size }} role="img" aria-label={`${label || 'Score'} ${value == null ? 'not available' : Math.round(v) + ' out of 100'}`}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#E6EDF7" strokeWidth="10" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - v / 100)} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </svg>
      <span style={{ fontSize: size / 3.2 }}>{value == null ? '-' : Math.round(v)}</span>
    </div>
  )
}

export const Kpi = ({ label, value, sub }) => (
  <div className="card kpi"><span className="label">{label}</span><span className="value">{value}</span>{sub && <span className="muted small">{sub}</span>}</div>
)

export const ScoreBadge = ({ value }) => <span className={`badge ${scoreTone(value)}`}>{value == null ? 'n/a' : `${Math.round(value)}/100`}</span>
