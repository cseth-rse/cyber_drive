// src/api/client.js
import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// In-memory access token (never in localStorage)
let _accessToken = null

export const setAccessToken = (t) => { _accessToken = t }
export const getAccessToken = () => _accessToken
export const clearAccessToken = () => { _accessToken = null }

const client = axios.create({
  baseURL: BASE,
  withCredentials: true,
})

// Attach bearer token to every request
client.interceptors.request.use((config) => {
  if (_accessToken) {
    config.headers['Authorization'] = `Bearer ${_accessToken}`
  }
  return config
})

// On 401, try to refresh once
let refreshing = false
let waitQueue = []

const processQueue = (err, token) => {
  waitQueue.forEach((p) => err ? p.reject(err) : p.resolve(token))
  waitQueue = []
}

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {

      // Don't attempt refresh if the refresh endpoint itself failed
      if (original.url?.includes('/auth/refresh')) {
        clearAccessToken()
        window.dispatchEvent(new CustomEvent('auth:logout'))
        return Promise.reject(err)
      }

      if (refreshing) {
        return new Promise((resolve, reject) => {
          waitQueue.push({ resolve, reject })
        }).then((token) => {
          original.headers['Authorization'] = `Bearer ${token}`
          return client(original)
        })
      }

      original._retry = true
      refreshing = true

      try {
        const { data } = await axios.post(`${BASE}/auth/refresh`, {}, { withCredentials: true })
        setAccessToken(data.access_token)
        processQueue(null, data.access_token)
        original.headers['Authorization'] = `Bearer ${data.access_token}`
        return client(original)
      } catch (refreshErr) {
        clearAccessToken()
        processQueue(refreshErr, null)
        window.dispatchEvent(new CustomEvent('auth:logout'))
        return Promise.reject(refreshErr)
      } finally {
        refreshing = false
      }
    }
    return Promise.reject(err)
  },
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const api = {
  auth: {
    register: (email) => client.post('/auth/register', { email }),
    verifyOtp: (email, otp) => client.post('/auth/verify-otp', { email, otp }),
    refresh: () => client.post('/auth/refresh'),
    logout: () => client.post('/auth/logout'),
  },
  levels: {
    list: () => client.get('/levels'),
    courses: (levelId) => client.get(`/levels/${levelId}/courses`),
  },
  documents: {
    list: (params) => client.get('/documents', { params }),
    get: (id) => client.get(`/documents/${id}`),
    fileUrl: (id) => `${BASE}/documents/${id}/file`,
    upload: (formData) =>
      client.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
  },
}

export default client