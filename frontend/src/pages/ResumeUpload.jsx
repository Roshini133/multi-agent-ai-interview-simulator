import { useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, UploadCloud } from 'lucide-react'
import { api } from '../services/api'
import { ErrorAlert, Stepper } from '../components/ui'
import { STEPS } from './Setup'

const SECTIONS = [['education', 'Education'], ['projects', 'Projects'], ['internships', 'Internships'], ['experience', 'Experience'], ['certifications', 'Certifications'], ['achievements', 'Achievements']]

export default function ResumeUpload() {
  const { id } = useParams()
  const nav = useNavigate()
  const input = useRef(null)
  const [parsed, setParsed] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [drag, setDrag] = useState(false)

  const upload = async (file) => {
    if (!file) return
    setError(null)
    if (!file.name.toLowerCase().endsWith('.pdf')) return setError('Please upload a PDF file.')
    if (file.size > 5 * 1024 * 1024) return setError('The resume must be smaller than 5 MB.')
    setBusy(true)
    try { setParsed((await api.uploadResume(id, file)).parsed) } catch (e) { setError(e) } finally { setBusy(false) }
  }

  return (
    <div className="container page" style={{ maxWidth: 860 }}>
      <Stepper steps={STEPS} current={1} />
      <h1 style={{ fontSize: '1.7rem' }}>Upload your resume</h1>
      <p className="muted">We extract your skills and projects to personalise questions. The PDF itself is not stored - only the extracted text.</p>
      <ErrorAlert error={error} />
      {!parsed && (
        <div className={`dropzone ${drag ? 'drag' : ''}`} style={{ margin: '16px 0' }} role="button" tabIndex={0}
          onClick={() => input.current.click()} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && input.current.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files[0]) }}>
          {busy ? <><span className="spinner" /><p>Analysing your resume...</p></> : <><UploadCloud size={36} color="#1565C0" /><p><b>Click to choose a PDF</b> or drag it here</p><p className="muted small">Text-based PDF, up to 5 MB</p></>}
          <input ref={input} type="file" accept="application/pdf,.pdf" hidden onChange={(e) => upload(e.target.files[0])} />
        </div>
      )}
      {parsed && (
        <div className="card" style={{ margin: '16px 0' }}>
          <div className="row" style={{ marginBottom: 10 }}><CheckCircle2 color="#1B7F4B" /><h3 style={{ margin: 0 }}>Resume analysed{parsed.name ? ` - ${parsed.name}` : ''}</h3></div>
          <p className="muted small">Please check that this looks right. If something is missing, the interview still works but is less personalised.</p>
          <h4>Skills detected ({parsed.skills.length})</h4>
          <div>{parsed.skills.length ? parsed.skills.map((s) => <span className="chip" key={s}>{s}</span>) : <span className="muted">None detected</span>}</div>
          <div className="grid g2" style={{ marginTop: 12 }}>
            {SECTIONS.filter(([k]) => parsed[k]?.length).map(([k, label]) => (
              <div key={k}><h4>{label}</h4><ul className="bul small">{parsed[k].slice(0, 4).map((x, i) => <li key={i}>{x}</li>)}</ul></div>))}
          </div>
          <button className="btn btn-ghost btn-sm" style={{ marginTop: 10 }} onClick={() => setParsed(null)}>Upload a different file</button>
        </div>
      )}
      <div className="row">
        <button className="btn btn-primary btn-lg" disabled={busy} onClick={() => nav(`/interview/${id}/device-check`)}>{parsed ? 'Continue' : 'Skip for now'}</button>
      </div>
    </div>
  )
}
