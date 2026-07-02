import { useParams } from 'react-router-dom'
import styles from './StubPage.module.css'

export default function NodeDetailPage() {
  const { nodeId } = useParams()
  return (
    <div className={styles.stub}>
      <div className={styles.icon}>🖥</div>
      <h2 className={styles.title}>Node detail coming soon</h2>
      <p className={styles.sub}>
        Full metrics and history for <code className={styles.code}>{nodeId}</code> will appear here.
      </p>
    </div>
  )
}
