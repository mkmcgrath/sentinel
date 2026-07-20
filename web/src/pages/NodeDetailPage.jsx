import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fetchLatestMetrics, fetchMetricHistory, fetchNode } from '../api'
import { metricColor, timeAgo } from '../utils'
import StatusBadge from '../components/StatusBadge'
import styles from './NodeDetailPage.module.css'

const REFRESH_INTERVAL = 10000
const RANGES = [
  { label: '1h', hours: 1 },
  { label: '6h', hours: 6 },
  { label: '24h', hours: 24 },
]

function formatTick(t) {
  return new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function cpuSeries(history) {
  return (history?.data ?? []).map((d) => ({ t: d.timestamp, v: d.data?.usage_percent ?? null }))
}

function memSeries(history) {
  return (history?.data ?? []).map((d) => ({ t: d.timestamp, v: d.data?.percent ?? null }))
}

function diskSeries(history) {
  return (history?.data ?? []).map((d) => {
    const partitions = d.data?.partitions ?? []
    const v = partitions.length ? Math.max(...partitions.map((p) => p.percent ?? 0)) : null
    return { t: d.timestamp, v }
  })
}

function MetricChart({ title, color, data, currentValue }) {
  return (
    <div className={styles.chartCard}>
      <div className={styles.chartHeader}>
        <span className={styles.chartTitle}>{title}</span>
        <span className={styles.chartValue} style={{ color: metricColor(currentValue) }}>
          {currentValue !== null && currentValue !== undefined ? `${Math.round(currentValue)}%` : '--'}
        </span>
      </div>
      {data.length === 0 ? (
        <div className={styles.chartEmpty}>No data for this range yet</div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="t"
              tickFormatter={formatTick}
              stroke="var(--text-dim)"
              tick={{ fontSize: 11 }}
              minTickGap={40}
            />
            <YAxis domain={[0, 100]} stroke="var(--text-dim)" tick={{ fontSize: 11 }} width={32} />
            <Tooltip
              contentStyle={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: 'var(--text-muted)' }}
              labelFormatter={formatTick}
              formatter={(value) => [`${Number(value).toFixed(1)}%`, title]}
            />
            <Line type="monotone" dataKey="v" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

function ServiceList({ latest }) {
  const services = latest?.metrics?.services?.data?.services ?? []
  const ports = latest?.metrics?.services?.data?.ports ?? []

  if (services.length === 0 && ports.length === 0) return null

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Services & Ports</h2>
      <div className={styles.pillGrid}>
        {services.map((s) => (
          <span key={s.name} className={[styles.pill, s.active ? styles.pillOk : styles.pillBad].join(' ')}>
            {s.name} <span className={styles.pillStatus}>{s.status}</span>
          </span>
        ))}
        {ports.map((p) => (
          <span key={p.port} className={[styles.pill, p.listening ? styles.pillOk : styles.pillBad].join(' ')}>
            :{p.port} <span className={styles.pillStatus}>{p.listening ? 'listening' : 'closed'}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

function ContainerList({ latest }) {
  const containers = latest?.metrics?.containers?.data ?? []
  if (containers.length === 0) return null

  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>Containers</h2>
      <div className={styles.containerTable}>
        <div className={[styles.containerRow, styles.containerHeaderRow].join(' ')}>
          <span>Name</span>
          <span>CPU</span>
          <span>Memory</span>
        </div>
        {containers.map((c) => (
          <div key={c.name} className={styles.containerRow}>
            <span>{c.name}</span>
            <span style={{ color: metricColor(c.cpu_percent) }}>{c.cpu_percent?.toFixed(1)}%</span>
            <span style={{ color: metricColor(c.mem_percent) }}>
              {c.mem_used_mb?.toFixed(0)} MB ({c.mem_percent?.toFixed(1)}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function NodeDetailPage() {
  const { nodeId } = useParams()
  const [rangeHours, setRangeHours] = useState(1)
  const [node, setNode] = useState(null)
  const [latest, setLatest] = useState(null)
  const [histories, setHistories] = useState({ cpu: null, memory: null, disk: null })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      const [nodeData, latestData, cpuHist, memHist, diskHist] = await Promise.all([
        fetchNode(nodeId),
        fetchLatestMetrics(nodeId),
        fetchMetricHistory(nodeId, 'cpu', rangeHours),
        fetchMetricHistory(nodeId, 'memory', rangeHours),
        fetchMetricHistory(nodeId, 'disk', rangeHours),
      ])
      setNode(nodeData)
      setLatest(latestData)
      setHistories({ cpu: cpuHist, memory: memHist, disk: diskHist })
      setError(null)
    } catch (err) {
      setError(err.message || 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [nodeId, rangeHours])

  useEffect(() => {
    setLoading(true)
    load()
    const id = setInterval(load, REFRESH_INTERVAL)
    return () => clearInterval(id)
  }, [load])

  if (loading) {
    return (
      <div className={styles.centered}>
        <div className="spinner" />
        <p className={styles.loadingText}>Loading {nodeId}…</p>
      </div>
    )
  }

  if (error && !node) {
    return (
      <div className={styles.centered}>
        <div className={styles.errorIcon}>⚡</div>
        <h2 className={styles.errorTitle}>Could not load node</h2>
        <p className={styles.errorMessage}>{error}</p>
        <Link to="/" className={styles.backLink}>← Back to dashboard</Link>
      </div>
    )
  }

  const cpuNow = latest?.metrics?.cpu?.data?.usage_percent ?? null
  const memNow = latest?.metrics?.memory?.data?.percent ?? null
  const diskPartitions = latest?.metrics?.disk?.data?.partitions ?? []
  const diskNow = diskPartitions.length ? Math.max(...diskPartitions.map((p) => p.percent ?? 0)) : null

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <Link to="/" className={styles.backLink}>← Back to dashboard</Link>

        <div className={styles.pageHeader}>
          <div>
            <div className={styles.titleRow}>
              <h1 className={styles.pageTitle}>{node?.hostname || nodeId}</h1>
              <StatusBadge status={node?.status} />
            </div>
            <p className={styles.pageSubtitle}>
              {nodeId} · last seen {timeAgo(node?.last_seen)}
            </p>
          </div>

          <div className={styles.rangeToggle}>
            {RANGES.map((r) => (
              <button
                key={r.label}
                className={[styles.rangeBtn, rangeHours === r.hours ? styles.rangeBtnActive : ''].join(' ')}
                onClick={() => setRangeHours(r.hours)}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {error && node && (
          <div className={styles.staleWarning}>⚠ Data may be stale — API unreachable: {error}</div>
        )}

        <div className={styles.chartGrid}>
          <MetricChart title="CPU" color="var(--accent)" data={cpuSeries(histories.cpu)} currentValue={cpuNow} />
          <MetricChart title="Memory" color="var(--green)" data={memSeries(histories.memory)} currentValue={memNow} />
          <MetricChart title="Disk" color="var(--yellow)" data={diskSeries(histories.disk)} currentValue={diskNow} />
        </div>

        <ServiceList latest={latest} />
        <ContainerList latest={latest} />
      </div>
    </div>
  )
}
