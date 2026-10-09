import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Download, Printer } from 'lucide-react'
import { api } from '../services/api'
import { ErrorAlert, Loading, ScoreBadge } from '../components/ui'
import IntegrityPanel from '../components/IntegrityPanel'
import { AGENTS, fmtDate, fmtTime, titleCase } from '../utils/format'
import { downloadReportPdf } from '../utils/download'

const List = ({ items }) => <ul className="bul">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>

export default function Report() {
  const { id } = useParams()
  const [r, setR] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => { api.report(id).then(setR).catch(setError) }, [id])
  if (error) return <div className="container page"><ErrorAlert error={error} /><Link to={`/results/${id}`} className="btn btn-secondary" style={{ marginTop: 12 }}>Back to dashboard</Link></div>
  if (!r) return <Loading label="Loading report..." />

  return (
    <div className="container page" style={{ maxWidth: 940 }}>
      <div className="row between wrap no-print" style={{ marginBottom: 16 }}>
        <Link to={`/results/${id}`} className="btn btn-ghost">Back to dashboard</Link>
        <div className="row"><button className="btn btn-ghost" onClick={() => window.print()}><Printer size={16} /> Print</button>
          <button className="btn btn-primary" onClick={() => downloadReportPdf(id).catch(setError)}><Download size={16} /> Download PDF</button></div>
      </div>
      <div className="card stack">
        <h1 style={{ fontSize: '1.7rem' }}>Interview report</h1>
        <div className="grid g4 small">
          <div><span className="muted">Candidate</span><br /><b>{r.candidate.name}</b></div><div><span className="muted">Role</span><br /><b>{r.role_label}</b></div>
          <div><span className="muted">Date</span><br /><b>{fmtDate(r.date)}</b></div><div><span className="muted">Duration</span><br /><b>{fmtTime(r.duration_seconds)}</b></div>
        </div>
        <div className="row"><b>Overall practice score:</b> <ScoreBadge value={r.scores.overall} /> <span className="badge">{r.readiness}</span></div>
        <div><h3>Executive summary</h3><p style={{ margin: 0 }}>{r.executive_summary}</p></div>
      </div>

      <h2 style={{ margin: '24px 0 10px' }}>Interviewer evaluations</h2>
      <div className="grid g3">
        {['hr', 'technical', 'manager'].map((k) => { const a = r.agent_reviews[k]; return (
          <div className="card" key={k}><div className="row between"><span className="badge">{AGENTS[k].label}</span><ScoreBadge value={a.score} /></div>
            <p className="small muted" style={{ margin: '8px 0 4px' }}>{a.name}</p><p>{a.summary}</p>
            {a.strengths.length > 0 && <><b className="small">Strengths</b><List items={a.strengths} /></>}
            {a.concerns.length > 0 && <><b className="small">To improve</b><List items={a.concerns} /></>}</div>) })}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Panel discussion</h3>
        {r.panel.discussion.map((d, i) => <div className="chat" key={i}><span className="who">{d.speaker}</span><span>{d.message}</span></div>)}
        <div className="feedback"><b>Final panel assessment</b><p style={{ margin: '6px 0 0' }}>{r.panel.final_assessment}</p>
          {r.panel.disagreement && <p className="small muted" style={{ margin: '6px 0 0' }}>{r.panel.disagreement}</p>}</div>
        <p className="small muted" style={{ marginBottom: 0, marginTop: 10 }}>{r.panel.disclaimer} Narrative source: {r.panel.source === 'llm' ? 'local LLM' : 'rule-based fallback'}.</p>
      </div>

      <div className="grid g2" style={{ marginTop: 16 }}>
        <div className="card"><h3>Strengths</h3><List items={r.scores.strengths.length ? r.scores.strengths : ['No metric averaged 7/10 or above.']} /></div>
        <div className="card"><h3>Weaknesses and improvements</h3><List items={r.scores.improvements.length ? r.scores.improvements : ['No major weaknesses identified.']} /></div>
        <div className="card"><h3>Technical topics to study</h3><List items={r.recommendations.technical_topics} /></div>
        <div className="card"><h3>Communication and behavioural tips</h3><List items={[...r.recommendations.communication, ...r.recommendations.behavioral]} /></div>
        <div className="card"><h3>Resume-based observations</h3><List items={r.resume_observations} /></div>
        <div className="card"><h3>Delivery metrics</h3><p className="small">Total words {r.speech_summary.total_words} | Avg words/answer {r.speech_summary.avg_words_per_answer} | Fillers {r.speech_summary.total_fillers} | Pace {r.speech_summary.avg_words_per_minute ?? 'n/a'} wpm | Voice answers {r.speech_summary.voice_answers}</p><p className="muted small" style={{ margin: 0 }}>{r.speech_summary.note}</p></div>
      </div>
      <div style={{ marginTop: 16 }}><IntegrityPanel integrity={r.integrity} /></div>

      <h2 style={{ margin: '24px 0 10px' }}>Question-by-question analysis</h2>
      {r.questions.map((q) => (
        <details className="qa" key={q.index}>
          <summary>Q{q.index} - {AGENTS[q.agent].short} | {q.difficulty} | {titleCase(q.topic || 'general')} <span style={{ float: 'right' }}><ScoreBadge value={q.overall * 10} /></span></summary>
          <div className="inner stack">
            <div><b>Question:</b> {q.question}</div><div><b>Your answer:</b> {q.answer}</div>
            <div className="row wrap">{Object.entries(q.scores).filter(([k, x]) => typeof x === 'number' && !['word_count', 'resume_alignment'].includes(k)).map(([k, x]) => <span className="chip" key={k}>{titleCase(k)}: {x}</span>)}</div>
            <div className="feedback"><b>Feedback:</b> {q.feedback}<br /><b>Improve:</b> {q.improvement}<div className="small muted" style={{ marginTop: 4 }}>Scored by: {q.method}</div></div>
          </div>
        </details>))}

      <div className="card" style={{ marginTop: 16 }}><h3>Methodology</h3><p className="small">{r.scores.method}</p>
        <p className="small"><b>Pretrained models:</b> {r.ai_components.pretrained_models.join('; ')}.</p>
        <p className="small"><b>Deterministic algorithms:</b> {r.ai_components.deterministic_algorithms.join('; ')}.</p><List items={r.disclaimers} /></div>
    </div>
  )
}
