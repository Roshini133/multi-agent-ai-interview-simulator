import { AGENTS } from '../utils/format'

const initials = (n = '') => n.split(' ').map((p) => p[0]).slice(0, 2).join('')

export default function AgentAvatar({ agent, name, title, speaking }) {
  const color = AGENTS[agent]?.color || '#1565C0'
  return (
    <div className="avatar-wrap">
      <div className={`avatar ${speaking ? 'speaking' : ''}`} style={{ background: color }} aria-hidden="true">{initials(name)}</div>
      <div>
        <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{name}</div>
        <div className="muted">{title}</div>
        <div className="row" style={{ gap: 8, marginTop: 6 }} aria-live="polite">
          <span className={`wave ${speaking ? 'on' : ''}`} aria-hidden="true">{[0, 1, 2, 3, 4, 5, 6].map((i) => <i key={i} />)}</span>
          <span className="small muted">{speaking ? 'Speaking...' : 'Listening'}</span>
        </div>
      </div>
    </div>
  )
}
