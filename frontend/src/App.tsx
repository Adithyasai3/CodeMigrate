import { useEffect, useState } from 'react'
import { Link, Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { api, getToken, setToken } from './api'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ScanView from './pages/ScanView'
import History from './pages/History'
import Compare from './pages/Compare'

export default function App() {
  const [email, setEmail] = useState<string | null>(null)
  const [checked, setChecked] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!getToken()) { setChecked(true); return }
    api.me().then(u => setEmail(u.email)).catch(() => setEmail(null)).finally(() => setChecked(true))
  }, [])

  const logout = () => { setToken(null); setEmail(null); navigate('/login') }
  if (!checked) return null
  const authed = email !== null

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">CodeMigrate</Link>
        <span className="tagline">Django upgrade checker · no proof, no claim</span>
        <nav>
          {authed && <NavLink to="/" end>New scan</NavLink>}
          {authed && <NavLink to="/history">History</NavLink>}
          <NavLink to="/compare">Compare systems</NavLink>
          {authed
            ? <button className="link" onClick={logout} title={email ?? ''}>Log out</button>
            : <NavLink to="/login">Log in</NavLink>}
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/login" element={<Login onLogin={setEmail} />} />
          <Route path="/" element={authed ? <Dashboard /> : <Navigate to="/login" />} />
          <Route path="/scans/:id" element={authed ? <ScanView /> : <Navigate to="/login" />} />
          <Route path="/history" element={authed ? <History /> : <Navigate to="/login" />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  )
}
