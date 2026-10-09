import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Download, FileText } from 'lucide-react'
import { api } from '../services/api'
import { ErrorAlert, Kpi, Loading, ScoreRing } from '../components/ui'
import { CategoryBars, CompetencyRadar, DifficultyChart, ScoreProgression } from '../components/Charts'
import IntegrityPanel from '../components/IntegrityPanel'
import { AGENTS, fmtDate, fmtTime, titleCase } from '../utils/format'
import { downloadReportPdf } from '../utils/download'

const v = (x) => (x == null ? '-' : x)

export default function Results() {
  const { id } = useParams()
  const [d, setD] = useState(null)
  const [error, setError] = useState(null)
  const [pdfBusy, setPdfBusy] = useState(false)
  useEffect(() => { api.dashboard(id).then(setD).catch(setError) }, [id])
  if (error) return <div className="container page"><ErrorAlert error={error} /></div>
  if (!d) return <Loading label="Loading your dashboard..." />
  const s = d.scores, c = s.competencies
  const done = d.status === 'completed'

  return (
    <div className="container page">
      <div className="row between wrap" style={{ marginBottom: 18 }}>
        <div><h1 style={{ fontSize: '1.7rem' }}>Performance dashboard</h1><p className="muted">{d.role_label} - {fmtDate(d.date)} - {d.candidate.name}</p></div>
        <div className="row wrap no-print">
          <Link className="btn btn-secondary" to={`/report/${id}`}><FileText size={16} /> Detailed report</Link>
          {done && <button className="btn btn-primary" disabled={pdfBusy} onClick={async () => { setPdfBusy(true); try { await downloadReportPdf(id) } catch (e) { setError(e) } finally { setPdfBusy(false) } }}><Download size={16} /> {pdfBusy ? 'Preparing...' : 'Download PDF'}</button>}
        </div>
      </div>
      {!done && <div style={{ marginBottom: 14 }}><ErrorAlert kind="warn" error="This interview is still in progress; scores are partial." /></div>}

      <div className="grid" style={{ gridTemplateColumns: 'minmax(220px, 260px) 1fr', marginBottom: 16 }}>
        <div className="card center"><div className="small muted" style={{ fontWeight: 600 }}>OVERALL PRACTICE SCORE</div><ScoreRing value={s.overall} size={150} label="Overall score" /><div style={{ fontWeight: 600 }}>{d.readiness || ''}</div></div>
        <div className="grid g3">
          <Kpi label="HR" value={v(s.agent_scores.hr)} sub="/100" /><Kpi label="Technical" value={v(s.agent_scores.technical)} sub="/100" /><Kpi label="Manager" value={v(s.agent_scores.manager)} sub="/100" />
          <Kpi label="Duration" value={fmtTime(d.duration_seconds)} /><Kpi label="Questions answered" value={`${d.questions_answered}/${d.total_questions}`} /><Kpi label="Resume relevance" value={v(s.categories.resume_relevance)} sub="/100" />
        </div>
      </div>

      <div className="grid g4" style={{ marginBottom: 16 }}>
        {[['Communication', c.communication], ['Clarity', c.clarity], ['Technical accuracy', c.technical_accuracy], ['Confidence', c.confidence], ['Completeness', c.completeness], ['Relevance', c.relevance]].map(([l, x]) => <Kpi key={l} label={l} value={v(x)} sub="/10" />)}
        <Kpi label="Avg pace" value={d.speech_summary.avg_words_per_minute ?? '-'} sub="words / minute" /><Kpi label="Filler words" value={d.speech_summary.total_fillers} sub={`${Math.round(d.speech_summary.filler_ratio * 100)}% of words`} />
      </div>

      <div className="grid g2" style={{ marginBottom: 16 }}>
        <div className="card"><h3>Competency radar</h3><CompetencyRadar competencies={c} /></div>
        <div className="card"><h3>Category scores</h3><CategoryBars categories={s.categories} labels={s.category_labels} /></div>
        <div className="card"><h3>Score progression</h3><ScoreProgression progression={s.progression} /></div>
        <div className="card"><h3>Adaptive difficulty progress</h3><DifficultyChart progress={d.difficulty_progress} /></div>
      </div>

      <div className="grid g2" style={{ marginBottom: 16 }}>
        <div className="card"><h3>Interview timeline</h3>
          <div className="timeline">{d.timeline.map((t) => (
            <div key={t.index}><b>Q{t.index}</b> <span className="badge" style={{ marginLeft: 6 }}>{AGENTS[t.agent].short}</span> <span className="badge muted">{t.difficulty}</span>
              <div className="small muted">{titleCase(t.topic || 'general')} - {Math.round(t.score)}/100</div></div>))}</div></div>
        <div className="stack">
          <div className="card"><h3>Strengths</h3><ul className="bul">{(s.strengths.length ? s.strengths : ['No metric averaged 7/10 or above yet.']).map((x) => <li key={x}>{x}</li>)}</ul></div>
          <div className="card"><h3>Improvement areas</h3><ul className="bul">{(s.improvements.length ? s.improvements : ['No major weaknesses identified.']).map((x) => <li key={x}>{x}</li>)}</ul></div>
        </div>
      </div>
      <IntegrityPanel integrity={d.integrity} />
      <p className="muted small" style={{ marginTop: 14 }}>{s.method}</p>
    </div>
  )
}
