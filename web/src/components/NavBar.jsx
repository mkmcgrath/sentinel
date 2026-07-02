import { NavLink } from 'react-router-dom'
import styles from './NavBar.module.css'

export default function NavBar() {
  return (
    <nav className={styles.nav}>
      <NavLink to="/" className={styles.brand}>
        <span className={styles.brandDot} />
        SENTINEL
      </NavLink>
      <div className={styles.links}>
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            [styles.link, isActive ? styles.active : ''].join(' ')
          }
        >
          Dashboard
        </NavLink>
        <NavLink
          to="/alerts"
          className={({ isActive }) =>
            [styles.link, isActive ? styles.active : ''].join(' ')
          }
        >
          Alerts
        </NavLink>
      </div>
    </nav>
  )
}
