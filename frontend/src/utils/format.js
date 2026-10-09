export const AGENTS = {
  hr: { label: 'HR Interviewer', short: 'HR', color: '#1565C0' },
  technical: { label: 'Technical Interviewer', short: 'Technical', color: '#0D47A1' },
  manager: { label: 'Hiring Manager', short: 'Manager', color: '#5C7CFA' },
}
export const fmtTime = (sec = 0) => {
  const s = Math.max(0, Math.floor(sec))
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60
  return (h ? `${h}:${String(m).padStart(2, '0')}` : String(m)) + `:${String(r).padStart(2, '0')}`
}
export const fmtDate = (iso) => (iso ? new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '-')
export const fmtScore = (v) => (v == null ? '-' : Math.round(v))
export const scoreTone = (v) => (v == null ? 'muted' : v >= 75 ? 'good' : v >= 55 ? 'ok' : 'low')
export const titleCase = (s = '') => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
