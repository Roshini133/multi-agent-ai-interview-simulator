import { Link } from 'react-router-dom'
import { BarChart3, Brain, Camera, FileText, Mic, ShieldCheck, Users, Video } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const features = [
  [Users, 'Multi-agent panel', 'HR, Technical and Manager interviewers each run their own round and then debate a balanced assessment.'],
  [Brain, 'Adaptive questioning', 'Question difficulty rises or eases with the quality of your answers, not a fixed script.'],
  [FileText, 'Resume-personalised', 'Upload your PDF resume and get questions about your own projects and skills.'],
  [Mic, 'Voice or text', 'Answer by speaking with live captions, or type. Delivery metrics like pace and fillers are tracked.'],
  [Video, 'Webcam observations', 'Approximate face and head-direction signals, processed locally and never recorded.'],
  [BarChart3, 'Transparent scoring', 'See every score, the formula behind it, and a downloadable PDF report.'],
]

export default function Landing() {
  const { user } = useAuth()
  return (
    <>
      <section className="hero">
        <div className="container hero-grid">
          <div>
            <span className="badge"><ShieldCheck size={14} /> Private, local AI - runs on your machine</span>
            <h1 style={{ marginTop: 14 }}>Practice. Perform. Improve.</h1>
            <p className="lead">A realistic virtual interview with an AI panel. Get adaptive questions, evidence-based feedback and a complete performance report - before the real interview.</p>
            <div className="row wrap">
              <Link className="btn btn-primary btn-lg" to={user ? '/setup' : '/register'}>{user ? 'Start an interview' : 'Start practising free'}</Link>
              {!user && <Link className="btn btn-secondary btn-lg" to="/login">Sign in</Link>}
            </div>
          </div>
          <div className="card" style={{ boxShadow: 'var(--shadow-lg)' }} aria-hidden="true">
            <div className="row between" style={{ marginBottom: 12 }}><span className="badge">Technical Interviewer</span><span className="small muted">Q 6 of 12 | 14:02</span></div>
            <div className="question-box">Can you explain why you selected Bi-LSTM for your pedestrian crossing prediction project?</div>
            <div className="grid g2" style={{ marginTop: 14 }}>
              <div className="video-box" style={{ aspectRatio: '16/10' }}><div className="video-off"><Camera /></div></div>
              <div className="stack"><div className="small muted">Approx. screen attention</div><div className="progress"><div style={{ width: '86%' }} /></div><div className="small muted">Difficulty</div><span className="badge ok">Medium - Hard</span></div>
            </div>
          </div>
        </div>
      </section>
      <section className="section container">
        <h2>Everything a real interview loop has</h2>
        <div className="grid g3">
          {features.map(([Icon, t, d]) => (
            <div className="card feature" key={t}><div className="ico"><Icon size={21} /></div><h3>{t}</h3><p className="muted" style={{ margin: 0 }}>{d}</p></div>
          ))}
        </div>
      </section>
      <section className="section container" style={{ paddingTop: 0 }}>
        <h2>How it works</h2>
        <div className="flow">
          {['Choose a role', 'Upload your resume', 'Check camera and mic', 'HR round', 'Technical round', 'Manager round', 'Panel discussion', 'Dashboard and PDF report'].map((s, i) => (
            <div key={s}><b>{i + 1}.</b> {s}</div>
          ))}
        </div>
      </section>
      <section className="section container" style={{ paddingTop: 0 }}>
        <div className="card"><h3><ShieldCheck size={18} style={{ verticalAlign: -3 }} /> Responsible AI</h3>
          <p className="muted" style={{ margin: 0 }}>Results are practice feedback, not hiring decisions. Gaze and webcam signals are approximate, can produce false positives, and are never evidence of dishonesty. They do not change your score. Video is analysed on the fly and is not stored.</p></div>
      </section>
    </>
  )
}
