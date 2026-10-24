import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Meta, type Project } from '../api'

const SAMPLE = `from django.contrib.auth.views import LogoutView
from django.db import models
from django.utils import timezone


class Order(models.Model):
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        index_together = [["created"]]

    def created_utc(self):
        return self.created.astimezone(timezone.utc)


class SiteLogout(LogoutView):
    def get_next_page(self):
        return "/"
`

export default function Dashboard() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<number | null>(null)
  const [newProject, setNewProject] = useState('')
  const [mode, setMode] = useState<'paste' | 'zip'>('paste')
  const [path, setPath] = useState('app/models.py')
  const [code, setCode] = useState(SAMPLE)
  const [zip, setZip] = useState<File | null>(null)
  const [fromV, setFromV] = useState('4.0')
  const [toV, setToV] = useState('5.1')
  const [provider, setProvider] = useState('offline')
  const [retriever, setRetriever] = useState('hybrid')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.meta().then(m => { setMeta(m); setFromV(m.default.from); setToV(m.default.to) }).catch(e => setError(String(e)))
    api.projects().then(ps => { setProjects(ps); if (ps.length) setProjectId(ps[0].id) }).catch(e => setError(String(e)))
  }, [])

  async function ensureProject(): Promise<number> {
    if (projectId) return projectId
    const p = await api.createProject(newProject || 'My Django project')
    setProjects([p, ...projects])
    setProjectId(p.id)
    return p.id
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const pid = await ensureProject()
      let scan
      if (mode === 'paste') {
        scan = await api.createScan(pid, { files: [{ path, content: code }], from_version: fromV, to_version: toV, provider, retriever })
      } else {
        if (!zip) throw new Error('Choose a .zip file first')
        const form = new FormData()
        form.append('file', zip)
        form.append('from_version', fromV)
        form.append('to_version', toV)
        form.append('provider', provider)
        form.append('retriever', retriever)
        scan = await api.uploadScan(pid, form)
      }
      navigate(`/scans/${scan.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setBusy(false)
    }
  }

  const versions = meta?.versions ?? ['4.0', '4.1', '4.2', '5.0', '5.1', '5.2']
  return (
    <section className="card">
      <h1>New scan</h1>
      <p className="muted">Findings are reported only when a validator confirms them against an official Django release-note entry.</p>
      <form onSubmit={submit} className="stack">
        <div className="row">
          <label>Project
            {projects.length > 0 ? (
              <select value={projectId ?? ''} onChange={e => setProjectId(e.target.value ? Number(e.target.value) : null)}>
                {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                <option value="">+ new project…</option>
              </select>
            ) : null}
          </label>
          {(projects.length === 0 || projectId === null) && (
            <label>New project name<input value={newProject} placeholder="My Django project" onChange={e => setNewProject(e.target.value)} /></label>
          )}
        </div>
        <div className="row">
          <label>From<select value={fromV} onChange={e => setFromV(e.target.value)}>{versions.map(v => <option key={v}>{v}</option>)}</select></label>
          <label>To<select value={toV} onChange={e => setToV(e.target.value)}>{versions.map(v => <option key={v}>{v}</option>)}</select></label>
          <label>Reasoner<select value={provider} onChange={e => setProvider(e.target.value)}>{(meta?.providers ?? ['offline']).map(p => <option key={p}>{p}</option>)}</select></label>
          <label>Retriever<select value={retriever} onChange={e => setRetriever(e.target.value)}>{(meta?.retrievers ?? ['hybrid']).map(r => <option key={r}>{r}</option>)}</select></label>
        </div>
        <div className="tabs" role="tablist">
          <button type="button" role="tab" aria-selected={mode === 'paste'} className={mode === 'paste' ? 'active' : ''} onClick={() => setMode('paste')}>Paste code</button>
          <button type="button" role="tab" aria-selected={mode === 'zip'} className={mode === 'zip' ? 'active' : ''} onClick={() => setMode('zip')}>Upload .zip</button>
        </div>
        {mode === 'paste' ? (
          <>
            <label>File path<input value={path} onChange={e => setPath(e.target.value)} /></label>
            <label>Code<textarea className="code" rows={18} value={code} onChange={e => setCode(e.target.value)} spellCheck={false} /></label>
          </>
        ) : (
          <label>Project archive (.zip, max 20 MB; venv/node_modules are skipped)
            <input type="file" accept=".zip" onChange={e => setZip(e.target.files?.[0] ?? null)} />
          </label>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? 'Submitting…' : 'Scan'}</button>
      </form>
    </section>
  )
}
