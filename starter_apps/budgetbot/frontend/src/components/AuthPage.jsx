import { useState } from 'react'
import { signIn, signUp, confirmSignUp, resendConfirmationCode } from '../auth/cognito.js'

/* ── TAB: login | register | confirm ── */
export default function AuthPage({ onAuthenticated }) {
  const [tab, setTab]           = useState('login')    // 'login' | 'register' | 'confirm'
  const [email, setEmail]       = useState('')
  const [name, setName]         = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode]         = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [pendingEmail, setPendingEmail] = useState('')

  const resetError = () => setError('')

  /* ── ĐĂNG NHẬP ── */
  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const token = await signIn(email, password)
      onAuthenticated(token, email)
    } catch (err) {
      if (err.code === 'UserNotConfirmedException') {
        setPendingEmail(email)
        setTab('confirm')
        setError('Tài khoản chưa xác nhận. Vui lòng nhập mã xác nhận đã gửi về Email.')
      } else if (err.code === 'NotAuthorizedException') {
        setError('Email hoặc mật khẩu không đúng.')
      } else if (err.code === 'UserNotFoundException') {
        setError('Tài khoản không tồn tại. Vui lòng đăng ký trước.')
      } else {
        setError(err.message || 'Đăng nhập thất bại.')
      }
    } finally {
      setLoading(false)
    }
  }

  /* ── ĐĂNG KÝ ── */
  const handleRegister = async (e) => {
    e.preventDefault()
    if (password.length < 8) {
      setError('Mật khẩu phải có ít nhất 8 ký tự.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await signUp(email, password, name)
      setPendingEmail(email)
      setTab('confirm')
      setError('')
    } catch (err) {
      if (err.code === 'UsernameExistsException') {
        setError('Email này đã được đăng ký. Vui lòng đăng nhập hoặc dùng email khác.')
      } else if (err.code === 'InvalidPasswordException') {
        setError('Mật khẩu quá yếu. Vui lòng thêm chữ hoa, số hoặc ký tự đặc biệt.')
      } else {
        setError(err.message || 'Đăng ký thất bại.')
      }
    } finally {
      setLoading(false)
    }
  }

  /* ── XÁC NHẬN EMAIL ── */
  const handleConfirm = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await confirmSignUp(pendingEmail || email, code)
      setTab('login')
      setError('')
      setCode('')
    } catch (err) {
      if (err.code === 'CodeMismatchException') {
        setError('Mã xác nhận không đúng. Vui lòng kiểm tra lại email.')
      } else if (err.code === 'ExpiredCodeException') {
        setError('Mã xác nhận đã hết hạn. Vui lòng đăng ký lại.')
      } else {
        setError(err.message || 'Xác nhận thất bại.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-bg">
      {/* Floating blobs */}
      <div className="auth-blob auth-blob-1" />
      <div className="auth-blob auth-blob-2" />
      <div className="auth-blob auth-blob-3" />

      <div className="auth-card">
        {/* Logo */}
        <div className="auth-logo">
          <span className="auth-logo-icon">💰</span>
        </div>
        <h1 className="auth-title">BudgetBot</h1>
        <p className="auth-subtitle">AI Money Coach · Quản lý tài chính thông minh</p>

        {/* Tabs */}
        {tab !== 'confirm' && (
          <div className="auth-tabs">
            <button
              className={`auth-tab${tab === 'login' ? ' active' : ''}`}
              onClick={() => { setTab('login'); resetError() }}
              id="tab-login"
            >
              Đăng nhập
            </button>
            <button
              className={`auth-tab${tab === 'register' ? ' active' : ''}`}
              onClick={() => { setTab('register'); resetError() }}
              id="tab-register"
            >
              Đăng ký
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="auth-error">
            <span>⚠️</span> {error}
          </div>
        )}

        {/* ── LOGIN FORM ── */}
        {tab === 'login' && (
          <form onSubmit={handleLogin} className="auth-form" autoComplete="on">
            <div className="auth-field">
              <label htmlFor="login-email">Email</label>
              <input
                id="login-email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={e => { setEmail(e.target.value); resetError() }}
                required
                autoComplete="email"
              />
            </div>
            <div className="auth-field">
              <label htmlFor="login-password">Mật khẩu</label>
              <input
                id="login-password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={e => { setPassword(e.target.value); resetError() }}
                required
                autoComplete="current-password"
              />
            </div>
            <button id="btn-login" type="submit" className="auth-btn" disabled={loading}>
              {loading ? <span className="spinner" /> : '🚀 Đăng nhập'}
            </button>
          </form>
        )}

        {/* ── REGISTER FORM ── */}
        {tab === 'register' && (
          <form onSubmit={handleRegister} className="auth-form" autoComplete="on">
            <div className="auth-field">
              <label htmlFor="reg-name">Họ và tên</label>
              <input
                id="reg-name"
                type="text"
                placeholder="Nguyễn Văn A"
                value={name}
                onChange={e => { setName(e.target.value); resetError() }}
                autoComplete="name"
              />
            </div>
            <div className="auth-field">
              <label htmlFor="reg-email">Email</label>
              <input
                id="reg-email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={e => { setEmail(e.target.value); resetError() }}
                required
                autoComplete="email"
              />
            </div>
            <div className="auth-field">
              <label htmlFor="reg-password">Mật khẩu</label>
              <input
                id="reg-password"
                type="password"
                placeholder="Ít nhất 8 ký tự"
                value={password}
                onChange={e => { setPassword(e.target.value); resetError() }}
                required
                autoComplete="new-password"
              />
            </div>
            <button id="btn-register" type="submit" className="auth-btn" disabled={loading}>
              {loading ? <span className="spinner" /> : '✨ Tạo tài khoản'}
            </button>
          </form>
        )}

        {/* ── CONFIRM FORM ── */}
        {tab === 'confirm' && (
          <form onSubmit={handleConfirm} className="auth-form">
            <p className="auth-confirm-hint">
              📧 Mã xác nhận đã được gửi tới <strong>{pendingEmail || email}</strong>.<br />
              Vui lòng kiểm tra hộp thư (kể cả Spam).
            </p>
            <div className="auth-field">
              <label htmlFor="confirm-code">Mã xác nhận (6 chữ số)</label>
              <input
                id="confirm-code"
                type="text"
                placeholder="123456"
                value={code}
                onChange={e => { setCode(e.target.value); resetError() }}
                required
                maxLength={6}
                style={{ letterSpacing: '0.3em', fontSize: '1.4rem', textAlign: 'center' }}
              />
            </div>
            <button id="btn-confirm" type="submit" className="auth-btn" disabled={loading}>
              {loading ? <span className="spinner" /> : '✅ Xác nhận tài khoản'}
            </button>
            <button
              type="button"
              className="auth-btn-ghost"
              onClick={() => { setTab('login'); resetError() }}
            >
              ← Quay lại đăng nhập
            </button>
          </form>
        )}

        <p className="auth-footer-note">
          Dữ liệu được mã hóa & bảo vệ bởi AWS Cognito 🔒
        </p>
      </div>
    </div>
  )
}
