import { ShieldCheck } from 'lucide-react'

export default function IntegrityPanel({ integrity }) {
  if (!integrity) return null
  const ratio = integrity.screen_attention_ratio
  return (
    <div className="card">
      <h3><ShieldCheck size={18} style={{ verticalAlign: -3 }} /> Behavioural observations &amp; integrity signals</h3>
      <div className="grid g2">
        <table className="tbl"><thead><tr><th>Observed signal</th><th>Events</th></tr></thead>
          <tbody>{integrity.signals.map((s) => <tr key={s.type}><td>{s.label}</td><td>{s.count}</td></tr>)}</tbody></table>
        <div className="stack">
          <div><div className="small muted">Approximate screen attention ratio</div>
            <div className="row"><div className="progress" style={{ flex: 1 }}><div style={{ width: `${ratio == null ? 0 : ratio * 100}%` }} /></div><b>{ratio == null ? 'n/a' : `${Math.round(ratio * 100)}%`}</b></div>
            <div className="small muted">{integrity.samples_analyzed} samples analysed. {integrity.attention_ratio_note}</div></div>
          <ul className="bul small">{integrity.observations.map((o, i) => <li key={i}>{o}</li>)}</ul>
        </div>
      </div>
      <div className="alert info" style={{ marginTop: 12 }}><ShieldCheck size={18} style={{ flexShrink: 0 }} /><div className="small">{integrity.disclaimer}</div></div>
    </div>
  )
}
