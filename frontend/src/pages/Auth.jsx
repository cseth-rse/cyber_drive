// src/pages/Auth.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '../components/Icons'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function Auth() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const { addToast } = useToast()

  const [step, setStep] = useState('email') // 'email' | 'otp'
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)

  const handleSendOtp = async (e) => {
    e.preventDefault()
    if (!email) return
    setLoading(true); setError('')
    try {
      await api.auth.register(email)
      setSent(true)
      setStep('otp')
      addToast(`OTP sent to ${email}`, 'success')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send OTP')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (e) => {
    e.preventDefault()
    if (!otp) return
    setLoading(true); setError('')
    try {
      const { data } = await api.auth.verifyOtp(email, otp)
      login(data.access_token, data.role, email)
      addToast('Welcome back!', 'success')
      navigate('/')
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Invalid or expired OTP')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
          <Icon id="i-cpu" size={22} />
          <span style={{ fontWeight: 900, fontSize: '1.1rem', letterSpacing: '-0.04em' }}>
            cyber<span style={{ color: 'var(--text3)', fontWeight: 300 }}>/</span>
            <span style={{ fontWeight: 300, color: 'var(--text2)' }}>drive</span>
          </span>
        </div>

        {step === 'email' ? (
          <>
            <h2 className="auth-title">Sign in</h2>
            <p className="auth-sub">We'll send a one-time code to your email address.</p>
            {error && <div className="auth-err">{error}</div>}
            <form onSubmit={handleSendOtp}>
              <div className="fld">
                <label>Email address <span className="req">*</span></label>
                <input
                  className="fi-n"
                  type="email"
                  placeholder="you@university.edu"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              <button className="btn" style={{ width: '100%', justifyContent: 'center', marginTop: 4 }} disabled={loading}>
                {loading ? <span className="spinner" /> : <><Icon id="i-login" size={14} /> Send OTP</>}
              </button>
            </form>
          </>
        ) : (
          <>
            <h2 className="auth-title">Check your inbox</h2>
            <p className="auth-sub">Enter the 6-digit code sent to <strong>{email}</strong>.</p>
            {sent && <div className="auth-ok">OTP sent! Check your email (or Ethereal preview in dev).</div>}
            {error && <div className="auth-err">{error}</div>}
            <form onSubmit={handleVerify}>
              <div className="fld">
                <label>One-time code <span className="req">*</span></label>
                <input
                  className="fi-n"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="123456"
                  value={otp}
                  onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
                  required
                  autoFocus
                  style={{ letterSpacing: '0.25em', fontSize: '1.3rem', textAlign: 'center' }}
                />
                <div className="fh">Code expires in 10 minutes.</div>
              </div>
              <button className="btn" style={{ width: '100%', justifyContent: 'center', marginTop: 4 }} disabled={loading || otp.length !== 6}>
                {loading ? <span className="spinner" /> : <><Icon id="i-ok" size={14} /> Verify & Sign In</>}
              </button>
              <button type="button" className="btn btn-gh" style={{ width: '100%', justifyContent: 'center', marginTop: 8 }} onClick={() => { setStep('email'); setError(''); setOtp('') }}>
                ← Use a different email
              </button>
              <button type="button" className="btn btn-ol" style={{ width: '100%', justifyContent: 'center', marginTop: 8 }} onClick={handleSendOtp} disabled={loading}>
                Resend OTP
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
