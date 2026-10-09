import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AGENTS, titleCase } from '../utils/format'

const BLUE = '#1565C0'
const H = 260

export function CompetencyRadar({ competencies }) {
  const data = Object.entries(competencies || {}).filter(([, v]) => v != null).map(([k, v]) => ({ metric: titleCase(k), value: v }))
  if (data.length < 3) return <p className="muted">Not enough data for a radar chart yet.</p>
  return (
    <ResponsiveContainer width="100%" height={H + 20}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid /><PolarAngleAxis dataKey="metric" tick={{ fontSize: 12 }} /><PolarRadiusAxis domain={[0, 10]} tick={{ fontSize: 10 }} />
        <Radar dataKey="value" name="Score (/10)" stroke={BLUE} fill={BLUE} fillOpacity={0.3} /><Tooltip />
      </RadarChart>
    </ResponsiveContainer>
  )
}

export function CategoryBars({ categories, labels }) {
  const data = Object.entries(categories || {}).filter(([, v]) => v != null).map(([k, v]) => ({ name: labels?.[k] || titleCase(k), score: v }))
  if (!data.length) return <p className="muted">No category scores yet.</p>
  return (
    <ResponsiveContainer width="100%" height={H}>
      <BarChart data={data} layout="vertical" margin={{ left: 30 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" domain={[0, 100]} /><YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 12 }} />
        <Tooltip /><Bar dataKey="score" fill={BLUE} radius={[0, 6, 6, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function ScoreProgression({ progression }) {
  if (!progression?.length) return <p className="muted">No answers recorded.</p>
  return (
    <ResponsiveContainer width="100%" height={H}>
      <LineChart data={progression} margin={{ right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="index" label={{ value: 'Question', position: 'insideBottom', offset: -2, fontSize: 12 }} /><YAxis domain={[0, 100]} />
        <Tooltip formatter={(v) => [`${v}/100`, 'Score']} labelFormatter={(i) => `Question ${i}`} />
        <Line type="monotone" dataKey="score" stroke={BLUE} strokeWidth={2.5} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

const LEVELS = { 1: 'Easy', 2: 'Medium', 3: 'Hard' }
export function DifficultyChart({ progress }) {
  if (!progress?.length) return <p className="muted">No difficulty data yet.</p>
  const data = progress.map((p) => ({ index: p.index, [AGENTS[p.agent]?.short || p.agent]: p.level }))
  const keys = [...new Set(progress.map((p) => AGENTS[p.agent]?.short || p.agent))]
  const merged = data.map((d) => ({ ...d }))
  const colors = { HR: '#1565C0', Technical: '#0D47A1', Manager: '#5C7CFA' }
  return (
    <ResponsiveContainer width="100%" height={H}>
      <LineChart data={merged} margin={{ right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="index" /><YAxis domain={[1, 3]} ticks={[1, 2, 3]} tickFormatter={(v) => LEVELS[v]} width={60} />
        <Tooltip formatter={(v) => LEVELS[v]} labelFormatter={(i) => `After question ${i}`} /><Legend />
        {keys.map((k) => <Line key={k} type="stepAfter" dataKey={k} stroke={colors[k]} strokeWidth={2.5} dot={{ r: 4 }} connectNulls />)}
      </LineChart>
    </ResponsiveContainer>
  )
}
