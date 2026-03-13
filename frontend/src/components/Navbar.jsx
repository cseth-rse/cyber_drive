// src/components/Navbar.jsx
import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Icon } from './Icons'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function Navbar({ theme, setTheme }) {
  const { user, logout } = useAuth()
  const { addToast } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  const active = (path) => location.pathname === path ? 'active' : ''

  const handleLogout = async () => {
    await logout()
    addToast('Logged out', 'info')
    navigate('/')
  }

  const go = (path) => { navigate(path); setMenuOpen(false) }

  const initials = user?.email ? user.email.slice(0, 2).toUpperCase() : '??'

  return (
    <>
      <nav className="navbar">
        <button className="nav-logo" onClick={() => go('/')} aria-label="cyber_drive home">
          <Icon id="i-cpu" size={17} />
          cyber<span className="n-slash">/</span><span className="n-sub">drive</span>
        </button>

        <div className="nav-c">
          <button className={`nav-link ${active('/')}`} onClick={() => go('/')}>
            <Icon id="i-home" size={13} />Home
          </button>
          <button className={`nav-link ${active('/materials')}`} onClick={() => go('/materials')}>
            <Icon id="i-layers" size={13} />Materials
          </button>
          {user && (
            <button className={`nav-link ${active('/upload')}`} onClick={() => go('/upload')}>
              <Icon id="i-upload" size={13} />Upload
            </button>
          )}
        </div>

        <div className="nav-r">
          <div className="t-switcher" role="group" aria-label="Theme selector">
            {[['dark','i-moon','Dark'],['light','i-sun','Light'],['hc','i-contrast','High Contrast']].map(([t, ic, label]) => (
              <button
                key={t}
                className={`t-btn ${theme === t ? 'active' : ''}`}
                onClick={() => setTheme(t)}
                aria-label={label}
                aria-pressed={theme === t}
              >
                <Icon id={ic} size={13} />
                <span className="tip">{label}</span>
              </button>
            ))}
          </div>

          {user ? (
            <>
              <button className="av-btn" onClick={() => go('/profile')} title={user.email}>
                {initials}
              </button>
              <button className="btn btn-gh btn-sm btn-ic" onClick={handleLogout} title="Log out">
                <Icon id="i-logout" size={14} />
              </button>
            </>
          ) : (
            <button className="btn btn-sm" onClick={() => go('/login')}>
              <Icon id="i-login" size={13} /> Sign in
            </button>
          )}

          <button
            className="hamburger"
            id="hbg"
            onClick={() => setMenuOpen(o => !o)}
            aria-label="Menu"
            aria-expanded={menuOpen}
          >
            <Icon id={menuOpen ? 'i-x' : 'i-menu'} size={20} />
          </button>
        </div>
      </nav>

      <div className={`mob-menu ${menuOpen ? 'open' : ''}`}>
        {[['/', 'i-home', 'Home'], ['/materials', 'i-layers', 'Materials'], ['/upload', 'i-upload', 'Upload'], ['/profile', 'i-user', 'Profile']].map(([path, ic, label]) => (
          <button key={path} className="nav-link" onClick={() => go(path)}>
            <Icon id={ic} size={14} /> {label}
          </button>
        ))}
      </div>
    </>
  )
}
