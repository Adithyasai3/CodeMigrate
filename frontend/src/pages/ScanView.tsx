import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, download, type Finding, type ScanDetail } from '../api'
import DiffView from '../components/DiffView'
import StatusBadge from '../components/StatusBadge'

export default function ScanView() {
  const { id } = useParams()
  const scanId = Number(id)
  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [file, setFile] = useState<string | null>(null)
  const [selected, setSelected] = useState<Finding | null>(null)
  const [showRejected, setShowRejected] = useState(false)
  const [view, setView] = useState<'original' | 'updated' | 'changes'>('original')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let timer: number | undefined
    const poll = () => api.scan(scanId).then(s => {
      setScan(s)
      if (s.status === 'PENDING' || s.status === 'RUNNING') timer = window.setTimeout(poll, 800)
    }).catch(e => setError(String(e)))
    poll()
    return () => window.clearTimeout(timer)
  }, [scanId])

  const findings = useMemo(() => scan?.result?.findings ?? [], [scan])
  const rejected = scan?.result?.rejected ?? []
  const files = scan?.sources ?? []
  const current = file ?? findings[0]?.file ?? files[0]?.path ?? null
  const source = files.find(f => f.path === current)?.content ?? ''
  const flagged = new Map(findings.filter(f => f.file === current).map(f => [f.line, f]))
  const updated = scan?.result?.updated_files?.find(u => u.path === current) ?? null
  const shown = updated ? view : 'original'

  const copyUpdated = async () => {
    if (!updated) return
    try {
      await navigator.clipboard.writeText(updated.content)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch { /* clipboard blocked: the download button still works */ }
  }

  const downloadUpdated = () => {
    if (!updated) return
    const url = URL.createObjectURL(new Blob([updated.content], { type: 'text/x-python' }))
    const a = document.createElement('a')
    a.href = url
    a.download = updated.path.split('/').pop() ?? 'updated.py'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (error) return <p className="error">{error}</p>
  if (!scan) return <p className="muted">Loading…</p>

  return (
    <section>
      <div className="card">
        <div className="row spread">
          <div>
            <h1>Scan #{scan.id} <StatusBadge status={scan.status} /></h1>
            <p className="muted">Django {scan.from_version} → {scan.to_version} · {scan.source_name} · reasoner {scan.provider} · retriever {scan.retriever}</p>
          </div>
          {scan.status === 'COMPLETED' && (
            <div className="row">
              <button onClick={() => download(`/api/scans/${scan.id}/report.md`, `codemigrate-scan-${scan.id}.md`)}>Export Markdown</button>
              <button onClick={() => download(`/api/scans/${scan.id}/report.pdf`, `codemigrate-scan-${scan.id}.pdf`)}>Export PDF</button>
            </div>
          )}
        </div>
        {scan.status === 'FAILED' && <p className="error">{scan.error}</p>}
        {scan.result && (
          <p className="stats">
            <strong>{findings.length}</strong> verified finding{findings.length === 1 ? '' : 's'} ·
            {' '}{scan.result.files_scanned} files · {scan.result.refs_found} API references ·
            {' '}{rejected.length} rejected claim{rejected.length === 1 ? '' : 's'} · {scan.result.latency_s.toFixed(1)} s
          </p>
        )}
      </div>

      {scan.result && (
        <div className="split">
          <div className="card">
            <h2>Findings</h2>
            {findings.length === 0 && <p className="muted">No verified breaking changes.</p>}
            <ul className="findings">
              {findings.map((f, i) => (
                <li key={i} className={selected === f ? 'selected' : ''}
                    onClick={() => { setFile(f.file); setSelected(f) }}>
                  <div className="row spread">
                    <code>{f.file}:{f.line}</code>
                    <span className={`badge type-${f.change_type || 'unknown'}`}>{f.change_type || 'change'}</span>
                  </div>
                  <div className="symbol">{f.symbol}</div>
                  <p>{f.explanation}</p>
                  {f.suggested_fix && <p className="fix">Fix: {f.suggested_fix}</p>}
                  <div className="cites">
                    <span className="badge verified" title="Citation checked by the validator">✓ {f.status}</span>
                    {f.source_urls.map((u, j) => (
                      <a key={u} href={u} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}>
                        {f.cited_ids[j] ?? 'release notes'} ↗
                      </a>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
            {rejected.length > 0 && (
              <>
                <button className="link" onClick={() => setShowRejected(!showRejected)}>
                  {showRejected ? 'Hide' : 'Show'} {rejected.length} rejected claim{rejected.length === 1 ? '' : 's'}
                </button>
                {showRejected && (
                  <ul className="findings rejected">
                    {rejected.map((f, i) => (
                      <li key={i}>
                        <code>{f.file}:{f.line}</code> <span className="badge rejected">{f.status}</span>
                        <div className="symbol">{f.symbol}</div>
                        <p className="muted">{f.reject_reason}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>

          <div className="card">
            <div className="row spread">
              <h2>Code</h2>
              {files.length > 1 && (
                <select value={current ?? ''} onChange={e => { setFile(e.target.value); setSelected(null) }}>
                  {files.map(f => <option key={f.path}>{f.path}</option>)}
                </select>
              )}
            </div>
            {updated && (
              <>
                <div className="row tabs" role="tablist">
                  {(['original', 'updated', 'changes'] as const).map(v => (
                    <button key={v} role="tab" aria-selected={shown === v}
                            className={shown === v ? 'tab active' : 'tab'} onClick={() => setView(v)}>
                      {v === 'original' ? 'Original' : v === 'updated' ? 'Updated code' : 'Changes'}
                    </button>
                  ))}
                </div>
                <p className="muted update-summary">
                  {updated.auto_fixed.length} fixed automatically
                  {updated.llm_fixed.length > 0 && <> · {updated.llm_fixed.length} fixed by the LLM (re-checked)</>}
                  {updated.manual.length > 0 && <> · {updated.manual.length} left as <code>TODO(codemigrate)</code> notes</>}
                </p>
              </>
            )}
            {shown === 'updated' && updated && (
              <>
                <div className="row">
                  <button onClick={copyUpdated}>{copied ? 'Copied ✓' : 'Copy'}</button>
                  <button onClick={downloadUpdated}>Download {updated.path.split('/').pop()}</button>
                </div>
                <pre className="codeview" aria-label={`Updated ${current}`}>
                  {updated.content.split('\n').map((text, i) => (
                    <div key={i} className={text.includes('# TODO(codemigrate)') ? 'line todo' : 'line'}>
                      <span className="ln">{i + 1}</span>{text || ' '}
                    </div>
                  ))}
                </pre>
              </>
            )}
            {shown === 'changes' && updated && <DiffView diff={updated.diff} />}
            {shown === 'original' && (
            <pre className="codeview" aria-label={`Source of ${current}`}>
              {source.split('\n').map((text, i) => {
                const n = i + 1
                const hit = flagged.get(n)
                return (
                  <div key={n} className={hit ? (selected === hit ? 'line hit active' : 'line hit') : 'line'}
                       title={hit ? hit.symbol : undefined}
                       onClick={() => hit && setSelected(hit)}>
                    <span className="ln">{n}</span>{text || ' '}
                  </div>
                )
              })}
            </pre>
            )}
            {shown === 'original' && selected?.patch && (
              <>
                <h3>Suggested patch (checked to parse)</h3>
                <DiffView diff={selected.patch} />
              </>
            )}
            {Object.keys(scan.result.file_errors).length > 0 && (
              <div className="error">
                {Object.entries(scan.result.file_errors).map(([p, e]) => <div key={p}>{p}: {e}</div>)}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
