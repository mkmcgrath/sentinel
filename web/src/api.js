const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8080'

async function request(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`)
  return res.json()
}

export async function fetchNodes() {
  return request('/api/v1/nodes')
}

export async function fetchActiveAlerts() {
  return request('/api/v1/alerts/events/active')
}

export async function fetchHealth() {
  return request('/api/v1/health')
}

export async function fetchNode(nodeId) {
  return request(`/api/v1/nodes/${nodeId}`)
}

export async function fetchLatestMetrics(nodeId) {
  return request(`/api/v1/metrics/latest/${nodeId}`)
}

export async function fetchMetricHistory(nodeId, metricType, hours = 24) {
  return request(`/api/v1/metrics/history/${nodeId}?metric_type=${metricType}&hours=${hours}`)
}
