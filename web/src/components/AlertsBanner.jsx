import { useNavigate } from 'react-router-dom'
import styles from './AlertsBanner.module.css'

export default function AlertsBanner({ count }) {
  const navigate = useNavigate()

  if (!count || count === 0) return null

  return (
    <button
      className={styles.banner}
      onClick={() => navigate('/alerts')}
      aria-label={`${count} active alert${count !== 1 ? 's' : ''} — click to view`}
    >
      <span className={styles.icon}>⚠</span>
      <span className={styles.text}>
        <strong>{count}</strong> active alert{count !== 1 ? 's' : ''}
      </span>
      <span className={styles.action}>View all →</span>
    </button>
  )
}
