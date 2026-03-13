// src/pages/Profile.jsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '../components/Icons'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

const BADGES = [
  { icon: 'i-rkt', nm: 'First Upload', ds: 'Uploaded your first resource' },
  { icon: 'i-star', nm: 'Top Contributor', ds: '50+ approved uploads' },
  { icon: 'i-ok', nm: 'Verified Expert', ds: '10 verified resources' },
  { icon: 'i-msg', nm: 'Helpful Voice', ds: '100+ upvoted comments' },
  { icon: 'i-book', nm: 'Librarian', ds: 'Uploaded across 5 courses' },
  { icon: 'i-trd', nm: 'Trending', ds: 'Resource got 200+ votes' },
  { icon: 'i-awd', nm: 'Legend', ds: 'Top contributor of the year' },
  { icon: 'i-usr', nm: 'Community Star', ds: 'Referred 20+ students' },
]

export default function Profile() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState('uploads')
  const [uploads, setUploads] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!user) { navigate('/login'); return }
    setLoading(true)
    api.documents.list({ page: 1, limit: 20 }).then(r => setUploads(r.data.items || [])).catch(() => {}).finally(() => setLoading(false))
  }, [user])

  if (!user) return null

  const initials = user.email.slice(0, 2).toUpperCase()

  return (
    <div className="pr-wrap">
      {/* Profile header */}
      <div className="pr-hdr">
        <div className="pr-av">{initials}</div>
        <div className="pr-info">
          <div className="pr-name">{user.email.split('@')[0]}</div>
          <div className="pr-hdl">@{user.email} · {user.role}</div>
          <div className="pr-bio">Computer Engineering student at Cyber University. Sharing materials to help the community.</div>
          <div className="pr-stats">
            <div><div className="ps-num">{uploads.length}</div><div className="ps-lbl">Uploads</div></div>
            <div><div className="ps-num">17</div><div className="ps-lbl">Saved</div></div>
            <div><div className="ps-num">12</div><div className="ps-lbl">Badges</div></div>
          </div>
        </div>
        <div className="pr-acts">
          <button className="btn btn-gh btn-sm">Edit Profile</button>
          <button className="btn btn-gh btn-sm" onClick={logout}><Icon id="i-logout" size={13} /> Log out</button>
        </div>
      </div>

      {/* Tabs */}
      <div className="pr-tabs">
        {[
          ['uploads', 'i-upload', `Uploads (${uploads.length})`],
          ['saved', 'i-bkm', 'Saved (17)'],
          ['badges', 'i-awd', 'Badges (12)'],
          ['activity', 'i-act', 'Activity'],
        ].map(([key, ic, label]) => (
          <button key={key} className={`pt ${tab === key ? 'on' : ''}`} onClick={() => setTab(key)} role="tab" aria-selected={tab === key}>
            <Icon id={ic} size={12} /> {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'uploads' && (
        <div>
          {loading
            ? <div className="loading-center"><div className="spinner" /></div>
            : uploads.length === 0
              ? <div className="empty"><Icon id="i-file" size={32} /><p>No uploads yet. <a onClick={() => navigate('/upload')} style={{cursor:'pointer'}}>Upload your first resource</a>.</p></div>
              : uploads.map(doc => (
                  <div key={doc.id} className="pu-it" onClick={() => navigate(`/document/${doc.id}`)}>
                    <div className="pu-ic"><Icon id="i-file" size={15} /></div>
                    <div className="pu-bd">
                      <div className="pu-ti">{doc.title}</div>
                      <div className="pu-mt">
                        <span>{doc.course?.code}</span>
                        <span>·</span>
                        <span><Icon id="i-dl" size={10} /> {doc.download_count}</span>
                        <span>·</span>
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                        <span>·</span>
                        <span style={{ color: doc.status === 'AVAILABLE' ? 'var(--upvote)' : 'var(--text3)' }}>{doc.status}</span>
                      </div>
                    </div>
                    <div className="pu-ac">
                      <button className="btn btn-gh btn-sm btn-ic" onClick={e => e.stopPropagation()}><Icon id="i-edit" size={12} /></button>
                    </div>
                  </div>
                ))
          }
        </div>
      )}

      {tab === 'saved' && (
        <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text2)', fontSize: '0.86rem' }}>
          17 saved materials · <a onClick={() => navigate('/materials')} style={{ cursor: 'pointer' }}>Browse to save more</a>
        </div>
      )}

      {tab === 'badges' && (
        <div className="bg-grid">
          {BADGES.map(b => (
            <div key={b.nm} className="bg-card">
              <div className="bg-ic"><Icon id={b.icon} size={26} /></div>
              <div className="bg-nm">{b.nm}</div>
              <div className="bg-ds">{b.ds}</div>
            </div>
          ))}
        </div>
      )}

      {tab === 'activity' && (
        <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text2)', fontSize: '0.86rem' }}>
          Recent activity will appear here.
        </div>
      )}
    </div>
  )
}
