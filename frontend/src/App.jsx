// src/App.jsx
import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import { SvgSprite } from './components/Icons'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Materials from './pages/Materials'
import Detail from './pages/Detail'
import Upload from './pages/Upload'
import Auth from './pages/Auth'
import Profile from './pages/Profile'

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('cd-theme') || 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('cd-theme', theme)
  }, [theme])

  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <SvgSprite />
          <Navbar theme={theme} setTheme={setTheme} />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/materials" element={<Materials />} />
            <Route path="/document/:id" element={<Detail />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/login" element={<Auth />} />
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
