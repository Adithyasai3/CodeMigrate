import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Scan } from '../api'
import StatusBadge from '../components/StatusBadge'

export default function History() {
  const [scans, setScans] = useState<Scan[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { api.scans().then(setScans).catch(e => setError(String(e))) }, [])
  if (error) return <p className="error">{error}</p>
  if (!scans) return <p className="muted">Loading…</p>
  return (
    <section className="card">
      <h1>Scan history</h1>
      {scans.length === 0 ? <p className="muted">No scans yet. <Link to="/">Run one.</Link></p> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>#</th><th>Source</th><th>Upgrade</th><th>Reasoner</th><th>Status</th><th className="num">Findings</th><th>Created</th></tr></thead>
            <tbody>
              {scans.map(s => (
                <tr key={s.id}>
                  <td><Link to={`/scans/${s.id}`}>{s.id}</Link></td>
                  <td>{s.source_name}</td>
                  <td>{s.from_version} → {s.to_version}</td>
                  <td>{s.provider}</td>
                  <td><StatusBadge status={s.status} /></td>
                  <td className="num">{s.findings_count}</td>
                  <td>{new Date(s.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
