import type { ScanStatus } from '../api'

const ICON: Record<ScanStatus, string> = { PENDING: '…', RUNNING: '⟳', COMPLETED: '✓', FAILED: '✕' }

export default function StatusBadge({ status }: { status: ScanStatus }) {
  return <span className={`badge status-${status.toLowerCase()}`}>{ICON[status]} {status}</span>
}
