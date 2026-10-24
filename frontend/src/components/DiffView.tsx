export default function DiffView({ diff }: { diff: string }) {
  return (
    <pre className="diff" aria-label="Unified diff">
      {diff.split('\n').map((line, i) => {
        const cls = line.startsWith('+++') || line.startsWith('---') ? 'meta'
          : line.startsWith('@@') ? 'hunk'
          : line.startsWith('+') ? 'add'
          : line.startsWith('-') ? 'del' : ''
        return <div key={i} className={cls}>{line || ' '}</div>
      })}
    </pre>
  )
}
