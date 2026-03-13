// src/pages/Home.jsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '../components/Icons'
import { api } from '../api/client'

const LEVEL_NAMES = { 1: 'First Year', 2: 'Second Year', 3: 'Third Year', 4: 'Fourth Year', 5: 'Final Year' }

function DocItem({ doc, onClick }) {
  return (
    <div className="fi" onClick={onClick} role="button" tabIndex={0} onKeyDown={e => e.key==='Enter' && onClick()}>
      <div className="v-col">
        <button className="v-btn" aria-label="Upvote" onClick={e => e.stopPropagation()}>
          <Icon id="i-up" size={12} />
        </button>
        <span className="v-ct">{doc.download_count ?? 0}</span>
        <button className="v-btn" aria-label="Downvote" onClick={e => e.stopPropagation()}>
          <Icon id="i-dn" size={12} />
        </button>
      </div>
      <div className="ty-ic"><Icon id="i-file" size={15} /></div>
      <div className="fi-main">
        <div className="fi-title">{doc.title}</div>
        <div className="fi-meta">
          <span className="fi-type">PDF</span>
          <span className="bul">·</span>
          <span>{doc.course?.code}</span>
          <span className="bul">·</span>
          <span>{doc.level?.name}</span>
          <span className="bul">·</span>
          <span><Icon id="i-dl" size={11} /> {doc.download_count}</span>
          <span className="bul">·</span>
          <span>{new Date(doc.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  )
}

export default function Home() {
  const navigate = useNavigate()
  const [levels, setLevels] = useState([])
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.levels.list().then(r => setLevels(r.data)),
      api.documents.list({ page: 1, limit: 4 }).then(r => setRecent(r.data.items || [])),
    ])
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      {/* Hero */}
      <div className="hero">
        <div className="h-badge"><span className="pulse" />Academic Repository · CompEng</div>
        <h1 className="h-title">All your academic<br /><span className="dim">materials, organised</span></h1>
        <p className="h-sub">Past questions, lecture notes, textbooks and guides — by level, course, and topic.</p>
        <div className="h-cta">
          <button className="btn btn-lg" onClick={() => navigate('/materials')}>
            <Icon id="i-layers" size={15} /> Browse Materials
          </button>
          <button className="btn btn-ol btn-lg" onClick={() => navigate('/upload')}>
            <Icon id="i-upload" size={15} /> Upload Resource
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="levels-wrap">
        <div className="stats-bar">
          <div className="s-item"><div className="s-num">2,847</div><div className="s-lbl">Resources</div></div>
          <div className="s-item"><div className="s-num">418</div><div className="s-lbl">Contributors</div></div>
          <div className="s-item"><div className="s-num">12,340</div><div className="s-lbl">Downloads</div></div>
          <div className="s-item"><div className="s-num">94%</div><div className="s-lbl">Satisfaction</div></div>
        </div>

        {/* Level cards */}
        <div className="sec-hdr">
          <div className="sec-title"><Icon id="i-grid" size={13} /> Academic Levels</div>
          <span className="sec-sub">100L – 500L</span>
        </div>
        <div className="lv-grid">
          {loading
            ? Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="lv-card" style={{ opacity: 0.4 }}>
                  <div className="lv-num">—</div>
                  <div className="lv-name">Loading…</div>
                </div>
              ))
            : levels.map((lv) => (
                <div
                  key={lv.id}
                  className="lv-card"
                  onClick={() => navigate(`/materials?level=${lv.id}`)}
                  tabIndex={0}
                  role="button"
                  onKeyDown={e => e.key==='Enter' && navigate(`/materials?level=${lv.id}`)}
                >
                  <div className="lv-num">{lv.name.replace('L', '')}</div>
                  <div className="lv-name">{LEVEL_NAMES[lv.order] || lv.name}</div>
                  <div className="lv-ct"><strong>{lv.courses?.length ?? 0}</strong> courses</div>
                </div>
              ))
          }
        </div>
      </div>

      {/* Recent uploads */}
      <div className="recent-wrap">
        <div className="sec-hdr">
          <div className="sec-title"><Icon id="i-zap" size={13} /> Recent Uploads</div>
          <button className="btn btn-gh btn-sm" onClick={() => navigate('/materials')}>
            View all <Icon id="i-right" size={11} />
          </button>
        </div>
        {loading
          ? <div className="loading-center"><div className="spinner" /></div>
          : recent.length === 0
            ? <div className="empty"><Icon id="i-file" size={32} /><p>No documents yet.</p></div>
            : recent.map(doc => (
                <DocItem key={doc.id} doc={doc} onClick={() => navigate(`/document/${doc.id}`)} />
              ))
        }
      </div>
    </div>
  )
}
