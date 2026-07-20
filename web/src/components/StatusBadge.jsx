import styles from './StatusBadge.module.css'

export default function StatusBadge({ status }) {
  const normalized = (status || '').toLowerCase()
  let cls = styles.badgeOffline

  if (normalized === 'online') cls = styles.badgeOnline
  else if (normalized === 'warning') cls = styles.badgeWarning

  return <span className={[styles.badge, cls].join(' ')}>{status || 'unknown'}</span>
}
