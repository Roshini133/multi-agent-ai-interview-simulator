import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ErrorAlert } from '../components/ui'

export default function Auth({ mode }) {
  const isLogin = mode === 'login'
  const { authenticate } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      await authenticate(mode, isLogin ? { email: form.email, password: form.password } : form)
      nav(loc.state?.from || '/dashboard', { replace: true })
    } catch (err) { setError(err) } finally { setBusy(false) }
  }

  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={submit} noValidate>
        <h2>{isLogin ? 'Welcome back' : 'Create your account'}</h2>
        <p className="muted">{isLogin ? 'Sign in to continue your interview practice.' : 'Free, local, and private.'}</p>
        <ErrorAlert error={error} />
        <div style={{ height: 12 }} />
        {!isLogin && <label className="field">Full name<input className="input" value={form.name} onChange={set('name')} autoComplete="name" required /></label>}
        <label className="field">Email<input className="input" type="email" value={form.email} onChange={set('email')} autoComplete="email" required /></label>
        <label className="field">Password<input className="input" type="password" value={form.password} onChange={set('password')} autoComplete={isLogin ? 'current-password' : 'new-password'} minLength={8} required />
          {!isLogin && <span className="muted small" style={{ fontWeight: 400 }}>At least 8 characters</span>}</label>
        <button className="btn btn-primary" style={{ width: '100%' }} disabled={busy}>{busy ? 'Please wait...' : isLogin ? 'Sign in' : 'Create account'}</button>
        <p className="center muted small" style={{ marginTop: 16 }}>{isLogin ? <>New here? <Link to="/register">Create an account</Link></> : <>Already registered? <Link to="/login">Sign in</Link></>}</p>
      </form>
    </div>
  )
}
