// src/pages/Materials.jsx
import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Icon } from '../components/Icons'
import { api } from '../api/client'

const LEVEL_NAMES = { 1: 'First Year', 2: 'Second Year', 3: 'Third Year', 4: 'Fourth Year', 5: 'Final Year' }

function DocCard({ doc, onClick }) {
  return (
    <div className="mc" onClick={onClick} role="button" tabIndex={0} onKeyDown={e => e.key==='Enter' && onClick()}>
      <div className="v-col">
        <button className="v-btn" onClick={e => e.stopPropagation()}><Icon id="i-up" size={12} /></button>
        <span className="v-ct">{doc.download_count ?? 0}</span>
        <button className="v-btn" onClick={e => e.stopPropagation()}><Icon id="i-dn" size={12} /></button>
      </div>
      <div className="m-ic"><Icon id="i-file" size={15} /></div>
      <div className="m-body">
        <div className="m-title">{doc.title}</div>
        <div className="m-desc">{doc.description || `Uploaded by ${doc.uploaded_by?.email}`}</div>
        <div className="m-tags">
          <span className="tag">PDF</span>
          <span className="tag">{doc.course?.code}</span>
        </div>
        <div className="m-ft">
          <span className="m-st"><Icon id="i-dl" size={11} /> {doc.download_count}</span>
          <span className="m-st">{new Date(doc.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  )
}

export default function Materials() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [levels, setLevels] = useState([])
  const [docs, setDocs] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('newest')
  const [page, setPage] = useState(1)

  const selectedLevel = params.get('level') ? Number(params.get('level')) : null
  const selectedCourse = params.get('course') || null

  useEffect(() => {
    api.levels.list().then(r => setLevels(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const q = { page, limit: 20 }
    if (selectedLevel) q.level_id = selectedLevel
    if (selectedCourse) q.course_id = selectedCourse
    api.documents.list(q)
      .then(r => { setDocs(r.data.items || []); setTotal(r.data.total || 0) })
      .catch(() => { setDocs([]); setTotal(0) })
      .finally(() => setLoading(false))
  }, [selectedLevel, selectedCourse, page])

  const currentLevel = levels.find(l => l.id === selectedLevel)
  const currentCourses = currentLevel?.courses || []

  return (
    <div>
      <div className="lp-hdr">
        <div className="bc">
          <a onClick={() => navigate('/')}>Home</a>
          <span className="sep"><Icon id="i-right" size={10} /></span>
          {currentLevel
            ? <><span onClick={() => { setParams({}); setPage(1) }} style={{cursor:'pointer',color:'var(--text2)'}}>{currentLevel.name}</span></>
            : <span>All Materials</span>
          }
        </div>
        <h2 className="lp-title">
          {currentLevel
            ? <><span className="dim">{currentLevel.name}</span> — {LEVEL_NAMES[currentLevel.order]}</>
            : 'All Materials'
          }
        </h2>
        <p className="lp-sub">{total} resources{currentLevel ? ` in ${currentLevel.name}` : ''}</p>
      </div>

      <div className="lv-layout">
        <aside className="sidebar">
          {/* Level filter */}
          <div className="sb-card">
            <div className="sb-title">Level</div>
            <button className={`f-item ${!selectedLevel ? 'on' : ''}`} onClick={() => { setParams({}); setPage(1) }}>
              <span className="f-ic"><Icon id="i-folder" size={12} /></span>
              All Levels
            </button>
            {levels.map(lv => (
              <button
                key={lv.id}
                className={`f-item ${selectedLevel === lv.id ? 'on' : ''}`}
                onClick={() => { setParams({ level: lv.id }); setPage(1) }}
              >
                <span className="f-ic"><Icon id="i-layers" size={12} /></span>
                {lv.name}
              </button>
            ))}
          </div>

          {/* Course filter (only when level selected) */}
          {currentCourses.length > 0 && (
            <div className="sb-card">
              <div className="sb-title">Course</div>
              <button
                className={`f-item ${!selectedCourse ? 'on' : ''}`}
                onClick={() => { setParams({ level: selectedLevel }); setPage(1) }}
              >
                All Courses
              </button>
              {currentCourses.map(c => (
                <button
                  key={c.id}
                  className={`f-item ${selectedCourse === c.id ? 'on' : ''}`}
                  onClick={() => { setParams({ level: selectedLevel, course: c.id }); setPage(1) }}
                >
                  <span className="f-ic"><Icon id="i-cpu" size={12} /></span>
                  {c.code}
                </button>
              ))}
            </div>
          )}
        </aside>

        <main className="mf">
          <div className="fc">
            <input
              className="s-inp"
              type="search"
              placeholder={`Search ${currentLevel ? currentLevel.name : 'all'} materials…`}
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <select className="sort-sel" value={sort} onChange={e => setSort(e.target.value)}>
              <option value="newest">Newest</option>
              <option value="downloads">Most Downloaded</option>
            </select>
          </div>

          {loading
            ? <div className="loading-center"><div className="spinner" /></div>
            : docs.length === 0
              ? <div className="empty"><Icon id="i-file" size={36} /><p>No documents found.</p></div>
              : docs
                  .filter(d => !search || d.title.toLowerCase().includes(search.toLowerCase()))
                  .map(doc => (
                    <DocCard key={doc.id} doc={doc} onClick={() => navigate(`/document/${doc.id}`)} />
                  ))
          }

          {/* Pagination */}
          {total > 20 && (
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 18 }}>
              <button className="btn btn-gh btn-sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
              <span style={{ alignSelf: 'center', fontSize: '0.8rem', color: 'var(--text3)' }}>Page {page}</span>
              <button className="btn btn-gh btn-sm" disabled={docs.length < 20} onClick={() => setPage(p => p + 1)}>Next →</button>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
