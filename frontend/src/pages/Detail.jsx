// src/pages/Detail.jsx
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Icon } from '../components/Icons'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

function fmt(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const RELATED_MOCK = [
  { title: 'Previous year exam', type: 'Past Q.', icon: 'i-file' },
  { title: 'Lecture Notes', type: 'Notes', icon: 'i-note' },
  { title: 'Textbook Reference', type: 'Textbook', icon: 'i-book' },
]

export default function Detail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { addToast } = useToast()
  const [doc, setDoc] = useState(null)
  const [loading, setLoading] = useState(true)
  const [comment, setComment] = useState('')

  useEffect(() => {
    setLoading(true)
    api.documents.get(id)
      .then(r => setDoc(r.data))
      .catch(() => addToast('Failed to load document', 'error'))
      .finally(() => setLoading(false))
  }, [id])

  const handleDownload = () => {
    if (!user) { navigate('/login'); return }
    const url = api.documents.fileUrl(id)
    window.open(url, '_blank')
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>
  if (!doc) return <div className="empty"><p>Document not found.</p></div>

  return (
    <div>
      <div style={{ maxWidth: 1040, margin: '0 auto', padding: '16px 20px 4px' }}>
        <div className="bc">
          <a onClick={() => navigate('/')}>Home</a>
          <span className="sep"><Icon id="i-right" size={10} /></span>
          <a onClick={() => navigate(`/materials?level=${doc.level?.id}`)}>{doc.level?.name}</a>
          <span className="sep"><Icon id="i-right" size={10} /></span>
          <span>{doc.course?.code} — {doc.title}</span>
        </div>
      </div>

      <div className="dl-layout">
        <div className="dl-main">
          {/* Title row */}
          <div className="dl-title-row">
            <div className="dl-vote" aria-label={`${doc.download_count} downloads`}>
              <button className="v-btn on"><Icon id="i-up" size={13} /></button>
              <span className="dl-v-num">{doc.download_count}</span>
              <button className="v-btn"><Icon id="i-dn" size={13} /></button>
            </div>
            <div>
              <div style={{ display: 'flex', gap: 5, marginBottom: 7, flexWrap: 'wrap' }}>
                <span className="tag">PDF</span>
                <span className="tag">{doc.course?.code}</span>
                {doc.level && <span className="tag">{doc.level.name}</span>}
              </div>
              <h1 className="dl-title">{doc.title}</h1>
            </div>
          </div>

          {/* Meta bar */}
          <div className="dl-meta">
            <span>By <strong>{doc.uploaded_by?.email}</strong></span>
            <span className="bul">·</span>
            <span>{new Date(doc.created_at).toLocaleDateString()}</span>
            <span className="bul">·</span>
            <span><strong>{doc.download_count}</strong> downloads</span>
            {doc.description && <><span className="bul">·</span><span style={{color:'var(--text3)'}}>{doc.description}</span></>}
            <div className="meta-acts">
              <button className="btn btn-sm" onClick={handleDownload}>
                <Icon id="i-dl" size={12} /> Download
              </button>
              <button className="btn btn-ol btn-sm" onClick={() => { navigator.clipboard.writeText(window.location.href); addToast('Link copied!') }}>
                <Icon id="i-share" size={12} /> Share
              </button>
            </div>
          </div>

          {/* PDF viewer */}
          <div className="pdf-vw">
            <div className="pdf-tb">
              <button className="btn btn-gh btn-sm btn-ic"><Icon id="i-up" size={13} /></button>
              <button className="btn btn-gh btn-sm btn-ic"><Icon id="i-dn" size={13} /></button>
              <span>{doc.file_name}</span>
              <button className="btn btn-gh btn-sm btn-ic"><Icon id="i-min" size={13} /></button>
              <button className="btn btn-gh btn-sm btn-ic"><Icon id="i-plus" size={13} /></button>
              <button className="btn btn-sm btn-ic" onClick={handleDownload}><Icon id="i-max" size={13} /></button>
            </div>
            <div className="pdf-body">
              <Icon id="i-file" size={44} style={{ color: 'var(--text3)' }} />
              <p style={{ fontWeight: 700, color: 'var(--text)' }}>{doc.file_name}</p>
              {user
                ? <><p>Click open to view this PDF in your browser.</p><button className="btn btn-sm" style={{ marginTop: 8 }} onClick={handleDownload}><Icon id="i-max" size={12} /> Open PDF</button></>
                : <><p>Sign in to view and download this document.</p><button className="btn btn-sm" style={{ marginTop: 8 }} onClick={() => navigate('/login')}>Sign In</button></>
              }
            </div>
          </div>

          {/* Comments section */}
          <div className="cm-sec">
            <h3 className="cm-hdr"><Icon id="i-msg" size={14} /> Comments</h3>
            {user ? (
              <div className="cm-box">
                <textarea
                  className="cm-ta"
                  placeholder="Share thoughts, corrections, or tips…"
                  value={comment}
                  onChange={e => setComment(e.target.value)}
                />
                <div className="cm-bf">
                  <button className="btn btn-gh btn-sm" onClick={() => setComment('')}>Cancel</button>
                  <button className="btn btn-sm" onClick={() => { setComment(''); addToast('Comment posted (demo)') }}>Post Comment</button>
                </div>
              </div>
            ) : (
              <div style={{ padding: '14px', color: 'var(--text3)', fontSize: '0.83rem', marginBottom: 14 }}>
                <a onClick={() => navigate('/login')} style={{ cursor: 'pointer' }}>Sign in</a> to leave a comment.
              </div>
            )}
          </div>
        </div>

        {/* Right sidebar */}
        <aside className="dl-sb">
          <div className="ic">
            <div className="ict"><Icon id="i-info" size={12} /> File Info</div>
            <div className="ir"><span className="lb"><Icon id="i-file" size={11} /> Type</span><span className="vl">PDF</span></div>
            <div className="ir"><span className="lb"><Icon id="i-layers" size={11} /> Size</span><span className="vl">{fmt(doc.size)}</span></div>
            <div className="ir"><span className="lb"><Icon id="i-ok" size={11} /> Status</span><span className="vl" style={{ color: 'var(--upvote)' }}>{doc.status}</span></div>
            <div className="ir"><span className="lb"><Icon id="i-dl" size={11} /> Downloads</span><span className="vl">{doc.download_count}</span></div>
            <button className="btn" style={{ width: '100%', marginTop: 9, justifyContent: 'center' }} onClick={handleDownload}>
              <Icon id="i-dl" size={13} /> Download
            </button>
          </div>

          <div className="ic">
            <div className="ict"><Icon id="i-lnk" size={12} /> Related</div>
            {RELATED_MOCK.map((r, i) => (
              <div key={i} className="ri" tabIndex={0}>
                <div className="ri-ic"><Icon id={r.icon} size={13} /></div>
                <div><div className="ri-title">{r.title}</div><div className="ri-meta">{r.type}</div></div>
              </div>
            ))}
            <button className="btn btn-gh btn-sm" style={{ width: '100%', justifyContent: 'center', marginTop: 7 }}
              onClick={() => navigate(`/materials?level=${doc.level?.id}&course=${doc.course_id}`)}>
              All {doc.course?.code} <Icon id="i-right" size={11} />
            </button>
          </div>

          <div className="ic">
            <div className="ict"><Icon id="i-tag" size={12} /> Tags</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              <span className="tag">{doc.course?.code}</span>
              <span className="tag">{doc.level?.name}</span>
              <span className="tag">PDF</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
