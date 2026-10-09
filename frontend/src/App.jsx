import { Route, Routes, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Landing from './pages/Landing'
import Auth from './pages/Auth'
import Dashboard from './pages/Dashboard'
import Setup from './pages/Setup'
import ResumeUpload from './pages/ResumeUpload'
import DeviceCheck from './pages/DeviceCheck'
import Lobby from './pages/Lobby'
import InterviewRoom from './pages/InterviewRoom'
import Completion from './pages/Completion'
import Results from './pages/Results'
import Report from './pages/Report'
import Settings from './pages/Settings'

const P = ({ children }) => <ProtectedRoute>{children}</ProtectedRoute>

export default function App() {
  return (
    <Routes>
      {/* Full-screen interview room (no site chrome) */}
      <Route path="/interview/:id/room" element={<P><InterviewRoom /></P>} />
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Auth mode="login" />} />
        <Route path="/register" element={<Auth mode="register" />} />
        <Route path="/dashboard" element={<P><Dashboard /></P>} />
        <Route path="/setup" element={<P><Setup /></P>} />
        <Route path="/interview/:id/resume" element={<P><ResumeUpload /></P>} />
        <Route path="/interview/:id/device-check" element={<P><DeviceCheck /></P>} />
        <Route path="/interview/:id/lobby" element={<P><Lobby /></P>} />
        <Route path="/interview/:id/complete" element={<P><Completion /></P>} />
        <Route path="/results/:id" element={<P><Results /></P>} />
        <Route path="/report/:id" element={<P><Report /></P>} />
        <Route path="/settings" element={<P><Settings /></P>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
