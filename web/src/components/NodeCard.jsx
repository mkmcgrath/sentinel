import { useNavigate } from 'react-router-dom'
import styles from './NodeCard.module.css'

function timeAgo(isoString) {
  if (!isoString) return 'never'
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (diff < 5) return 'just now'
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function metricColor(value) {
  if (value === null || value === undefined) return 'var(--border)'
  if (value >= 80) return 'var(--red)'
  if (value >= 60) return 'var(--yellow)'
  return 'var(--green)'
}

function MetricRow({ label, value }) {
  const display = value !== null && value !== undefined ? `${Math.round(value)}%` : '--'
  const pct = value !== null && value !== undefined ? Math.min(100, Math.max(0, value)) : 0
  const color = metricColor(value)

  return (
    <div className={styles.metricRow}>
      <span className={styles.metricLabel}>{label}</span>
      <div className={styles.progressTrack}>
        <div
          className={styles.progressFill}
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className={styles.metricValue} style={{ color }}>
        {display}
      </span>
    </div>
  )
}

function StatusBadge({ status }) {
  const normalized = (status || '').toLowerCase()
  let cls = styles.badgeOffline
  let label = status || 'unknown'

  if (normalized === 'online') cls = styles.badgeOnline
  else if (normalized === 'warning') cls = styles.badgeWarning

  return <span className={[styles.badge, cls].join(' ')}>{label}</span>
}

export default function NodeCard({ node }) {
  const navigate = useNavigate()
  const name = node.hostname || node.node_id

  return (
    <button
      className={styles.card}
      onClick={() => navigate(`/node/${node.node_id}`)}
      aria-label={`View details for node ${name}`}
    >
      <div className={styles.header}>
        <span className={styles.name}>{name}</span>
        <StatusBadge status={node.status} />
      </div>

      <div className={styles.metrics}>
        <MetricRow label="CPU" value={node.last_cpu_percent} />
        <MetricRow label="MEM" value={node.last_memory_percent} />
        <MetricRow label="DISK" value={node.last_disk_percent} />
      </div>

      <div className={styles.footer}>
        <span className={styles.lastSeen}>
          Last seen <span className={styles.timestamp}>{timeAgo(node.last_seen)}</span>
        </span>
        <span className={styles.viewLink}>Details →</span>
      </div>
    </button>
  )
}
