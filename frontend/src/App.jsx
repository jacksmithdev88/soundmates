import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import './App.css'
import HomePage from './Home'
import Dashboard from './Dashboard'
import Game from './Game'
import JoinRoomPage from './JoinRoom'
import { apiFetch, logout } from './api/client'

function RequireAuth({ children }) {
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let isMounted = true

    apiFetch('/user/auth/session')
      .then((session) => {
        if (isMounted) {
          setStatus(session.authenticated ? 'authenticated' : 'unauthenticated')
        }
      })
      .catch(() => {
        if (isMounted) setStatus('unauthenticated')
      })

    return () => {
      isMounted = false
    }
  }, [])

  if (status === 'loading') {
    return <main>Loading...</main>
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/" replace />
  }

  return children
}


function HomeRoute() {
  const [isAuthenticated, setIsAuthenticated] = useState(null)

  useEffect(() => {
    let isMounted = true

    apiFetch('/user/auth/session')
      .then((session) => {
        if (isMounted) setIsAuthenticated(session.authenticated)
      })
      .catch(() => {
        if (isMounted) setIsAuthenticated(false)
      })

    return () => {
      isMounted = false
    }
  }, [])

  if (isAuthenticated === null) {
    return <main>Loading...</main>
  }

  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <HomePage />
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRoute />} />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route
        path="/game/:roomCode"
        element={
          <RequireAuth>
            <Game />
          </RequireAuth>
        }
      />
      <Route path="/join/:roomCode" element={<JoinRoomPage />} />
    </Routes>
  )
}

export default App
