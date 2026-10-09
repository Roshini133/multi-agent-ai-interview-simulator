import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <div className="center" style={{ padding: 80 }}><span className="spinner" /></div>
  return user ? children : <Navigate to="/login" state={{ from: loc.pathname }} replace />
}
