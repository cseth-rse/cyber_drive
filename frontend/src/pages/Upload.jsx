// src/pages/Upload.jsx
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '../components/Icons'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function Upload() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { addToast } = useToast()
  const fileInputRef = useRef()

  const [levels, setLevels] = useState([])
  const [courses, setCourses] = useState([])
  const [dragOver, setDragOver] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const [form, setForm] = useState({
    file: null,
    title: '',
    description: '',
    levelId: '',
    courseId: '',
  })
  const [tags, setTags] = useState([])
  const [tagInput, setTagInput] = useState('')

  useEffect(() => {
    if (!user) { navigate('/login'); return }
    api.levels.list().then(r => setLevels(r.data)).catch(() => {})
  }, [user])

  useEffect(() => {
    if (!form.levelId) { setCourses([]); return }
    api.levels.courses(form.levelId).then(r => setCourses(r.data)).catch(() => setCourses([]))
  }, [form.levelId])

  const setField = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setField('file', f)
  }

  const addTag = () => {
    const v = tagInput.trim()
    if (v && !tags.includes(v)) setTags(t => [...t, v])
    setTagInput('')
  }

  const handleSubmit = async () => {
    if (!form.file)     { addToast('Please select a file', 'error');      return }
    if (!form.title)    { addToast('Title is required', 'error');          return }
    if (!form.levelId)  { addToast('Academic level is required', 'error'); return }
    if (!form.courseId) { addToast('Course is required', 'error');         return }

    const fd = new FormData()
    fd.append('file',        form.file)
    fd.append('title',       form.title)
    fd.append('description', form.description)
    fd.append('level_id',    form.levelId)
    fd.append('course_id',   form.courseId)

    setSubmitting(true)
    try {
      const { data } = await api.documents.upload(fd)
      addToast('Document submitted! It will be available once processed.', 'success', 5000)
      navigate(`/document/${data.id}`)
    } catch (err) {
      if (err.response?.status === 409) {
        addToast('A document with this title already exists. Please use a different title.', 'error')
      } else {
        const msg = err.response?.data?.detail || err.response?.data?.message || 'Upload failed'
        addToast(typeof msg === 'string' ? msg : JSON.stringify(msg), 'error')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="up-wrap">
      <h2 className="up-title">Upload Resource</h2>
      <p className="up-sub">Share academic materials with fellow students. Admin-verified before publishing.</p>

      {/* File drop zone */}
      <div className="fs">
        <div className="fs-title"><Icon id="i-upload" size={12} /> File</div>
        <div
          className={`dz ${dragOver ? 'drag-over' : ''}`}
          tabIndex={0}
          role="button"
          onClick={() => fileInputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onKeyDown={e => e.key === 'Enter' && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={e => setField('file', e.target.files[0])}
          />
          <div className="dz-ic"><Icon id="i-upload" size={38} /></div>
          {form.file ? (
            <>
              <div className="dz-t" style={{ color: 'var(--acc)' }}>{form.file.name}</div>
              <div className="dz-s">{(form.file.size / (1024 * 1024)).toFixed(2)} MB — Click to change</div>
            </>
          ) : (
            <>
              <div className="dz-t">Drop your file here or click to browse</div>
              <div className="dz-s">PDF only · Max 50 MB</div>
            </>
          )}
        </div>
      </div>

      {/* Details */}
      <div className="fs">
        <div className="fs-title"><Icon id="i-info" size={12} /> Details</div>
        <div className="fld">
          <label>Title <span className="req">*</span></label>
          <input
            className="fi-n"
            type="text"
            placeholder="e.g. CPE 331 — Data Structures 2019 Final Exam"
            value={form.title}
            onChange={e => setField('title', e.target.value)}
          />
        </div>
        <div className="fld">
          <label>Description</label>
          <textarea
            className="fi-n"
            placeholder="Brief description…"
            value={form.description}
            onChange={e => setField('description', e.target.value)}
          />
          <div className="fh">Optional — helps others find your upload.</div>
        </div>
        <div className="g2">
          <div className="fld">
            <label>Academic Level <span className="req">*</span></label>
            <select
              className="fi-n"
              value={form.levelId}
              onChange={e => { setField('levelId', e.target.value); setField('courseId', '') }}
            >
              <option value="">— Select —</option>
              {levels.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
          <div className="fld">
            <label>Course <span className="req">*</span></label>
            <select
              className="fi-n"
              value={form.courseId}
              onChange={e => setField('courseId', e.target.value)}
              disabled={!form.levelId}
            >
              <option value="">— Select —</option>
              {courses.map(c => <option key={c.id} value={c.id}>{c.code} — {c.title}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Tags */}
      <div className="fs">
        <div className="fs-title"><Icon id="i-tag" size={12} /> Tags</div>
        <div className="fld">
          <label>Add Tags</label>
          <div className="ti-wrap">
            <input
              className="fi-n"
              type="text"
              placeholder="Type a tag and press Enter…"
              value={tagInput}
              onChange={e => setTagInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addTag())}
            />
            <button className="btn btn-sm" onClick={addTag}>
              <Icon id="i-plus" size={11} /> Add
            </button>
          </div>
          <div className="chips">
            {tags.map(t => (
              <span key={t} className="chip">
                {t}
                <button onClick={() => setTags(ts => ts.filter(x => x !== t))} aria-label="Remove">×</button>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="fa">
        <button className="btn btn-gh" onClick={() => navigate(-1)}>Cancel</button>
        <button className="btn" disabled={submitting} onClick={handleSubmit}>
          {submitting ? <span className="spinner" /> : <Icon id="i-upload" size={12} />}
          {' '}Submit for Review
        </button>
      </div>
    </div>
  )
}