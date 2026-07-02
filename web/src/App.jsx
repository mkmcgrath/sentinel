import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import NavBar from './components/NavBar'
import HomePage from './pages/HomePage'
import NodeDetailPage from './pages/NodeDetailPage'
import AlertsPage from './pages/AlertsPage'

function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/node/:nodeId" element={<NodeDetailPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
