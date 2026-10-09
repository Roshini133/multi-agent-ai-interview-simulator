import { api } from '../services/api'

export async function downloadReportPdf(id) {
  const blob = await api.reportPdf(id)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `interview-report-${id.slice(0, 8)}.pdf`
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
