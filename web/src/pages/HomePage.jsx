import { useState, useEffect, useCallback } from 'react'
import { fetchNodes, fetchActiveAlerts, fetchHealth } from '../api'
import NodeCard from '../components/NodeCard'
import AlertsBanner from '../components/AlertsBanner'
import styles from './HomePage.module.css'

const REFRESH_INTERVAL = 5000

function LoadingState() {
  return (
    <div className={styles.centered}>
      <div className="spinner" />
      <p className={styles.loadingText}>Connecting to Sentinel…</p>
    </div>
  )
}

function ErrorState({ message, onRetry }) {
  return (
    <div className={styles.centered}>
      <div className={styles.errorIcon}>⚡</div>
      <h2 className={styles.errorTitle}>Could not reach the API</h2>
      <p className={styles.errorMessage}>{message}</p>
      <button className={styles.retryBtn} onClick={onRetry}>
        Retry
      </button>
    </div>
  )
}

export default function HomePage() {
  const [nodes, setNodes] = useState([])
  const [alerts, setAlerts] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      const [nodesData, alertsData, healthData] = await Promise.all([
        fetchNodes(),
        fetchActiveAlerts(),
        fetchHealth(),
      ])
      setNodes(nodesData)
      setAlerts(alertsData)
      setHealth(healthData)
      setError(null)
    } catch (err) {
      setError(err.message || 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, REFRESH_INTERVAL)
    return () => clearInterval(id)
  }, [load])

  if (loading) return <LoadingState />
  if (error && nodes.length === 0) return <ErrorState message={error} onRetry={load} />

  const stats = health?.statistics ?? {}
  const totalNodes = stats.total_nodes ?? nodes.length
  const onlineNodes = stats.online_nodes ?? nodes.filter(n => n.status === 'online').length
  const totalMetrics = stats.total_metrics ?? null

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        {/* Page header */}
        <div className={styles.pageHeader}>
          <div>
            <h1 className={styles.pageTitle}>Infrastructure Overview</h1>
            <p className={styles.pageSubtitle}>
              Monitoring {totalNodes} node{totalNodes !== 1 ? 's' : ''} across your homelab
            </p>
          </div>
          <div className={styles.liveIndicator}>
            <span className={styles.liveDot} />
            Live
          </div>
        </div>

        {/* Alerts banner */}
        {alerts.length > 0 && <AlertsBanner count={alerts.length} />}

        {/* Error while data is stale */}
        {error && nodes.length > 0 && (
          <div className={styles.staleWarning}>
            ⚠ Data may be stale — API unreachable: {error}
          </div>
        )}

        {/* Node grid */}
        {nodes.length === 0 ? (
          <div className={styles.empty}>
            <p className={styles.emptyIcon}>🖥</p>
            <p className={styles.emptyTitle}>No nodes registered</p>
            <p className={styles.emptyText}>
              Deploy the Sentinel agent on a machine to start monitoring it.
            </p>
          </div>
        ) : (
          <div className={styles.grid}>
            {nodes.map(node => (
              <NodeCard key={node.node_id} node={node} />
            ))}
          </div>
        )}
      </div>

      {/* Stats footer */}
      <footer className={styles.statsBar}>
        <span className={styles.stat}>
          <span className={styles.statValue}>{totalNodes}</span> nodes total
        </span>
        <span className={styles.divider}>·</span>
        <span className={styles.stat}>
          <span className={[styles.statValue, styles.statOnline].join(' ')}>{onlineNodes}</span> online
        </span>
        {totalMetrics !== null && (
          <>
            <span className={styles.divider}>·</span>
            <span className={styles.stat}>
              <span className={styles.statValue}>{totalMetrics.toLocaleString()}</span> metrics collected
            </span>
          </>
        )}
      </footer>
    </div>
  )
}
