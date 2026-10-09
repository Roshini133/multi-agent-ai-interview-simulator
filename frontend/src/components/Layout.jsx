import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { GraduationCap, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export function Brand() {
  return (
    <Link to="/" className="brand" aria-label="AI Interview Simulator home">
      <span className="brand-mark"><GraduationCap size={19} /></span>
      <span>AI Interview Simulator</span>
    </Link>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  return (
    <>
      <header className="nav">
        <div className="container nav-inner">
          <Brand />
          <nav className="nav-links" aria-label="Main">
            {user ? (
              <>
                <NavLink to="/dashboard">Dashboard</NavLink>
                <NavLink to="/setup">New interview</NavLink>
                <NavLink to="/settings">Settings</NavLink>
                <button className="link" onClick={() => { logout(); nav('/') }} aria-label="Sign out"><LogOut size={15} style={{ verticalAlign: -2 }} /> Sign out</button>
              </>
            ) : (
              <>
                <NavLink to="/login">Sign in</NavLink>
                <Link to="/register" className="btn btn-primary btn-sm">Get started</Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main><Outlet /></main>
      <footer className="footer">
        <div className="container row between wrap">
          <span>AI Interview Simulator - Practice. Perform. Improve.</span>
          <span>Practice assessments only; not an employment decision tool.</span>
        </div>
      </footer>
    </>
  )
}
