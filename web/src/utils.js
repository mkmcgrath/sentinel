export function timeAgo(isoString) {
  if (!isoString) return 'never'
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (diff < 5) return 'just now'
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export function metricColor(value) {
  if (value === null || value === undefined) return 'var(--border)'
  if (value >= 80) return 'var(--red)'
  if (value >= 60) return 'var(--yellow)'
  return 'var(--green)'
}
