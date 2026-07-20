import { useNavigate } from 'react-router-dom'
import { timeAgo, metricColor } from '../utils'
import StatusBadge from './StatusBadge'
import styles from './NodeCard.module.css'

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
