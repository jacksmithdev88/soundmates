import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiFetch, loginWithSpotify } from './api/client'
import { useRooms } from './hooks/useRooms'

function JoinRoomPage() {
  const { roomCode } = useParams()
  const navigate = useNavigate()
  const safeRoomCode = (roomCode || '').toUpperCase()
  const [authStatus, setAuthStatus] = useState('loading')
  const [hasAttemptedJoin, setHasAttemptedJoin] = useState(false)
  const { joinRoom, error } = useRooms()

  useEffect(() => {
    let isMounted = true

    apiFetch('/user/auth/session')
      .then((session) => {
        if (isMounted) setAuthStatus(session.authenticated ? 'authenticated' : 'unauthenticated')
      })
      .catch(() => {
        if (isMounted) setAuthStatus('unauthenticated')
      })

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    if (authStatus !== 'authenticated' || hasAttemptedJoin || !safeRoomCode) return

    setHasAttemptedJoin(true)

    joinRoom(safeRoomCode).then((success) => {
      if (success) {
        navigate('/dashboard', { replace: true })
      }
    })
  }, [authStatus, hasAttemptedJoin, safeRoomCode, joinRoom, navigate])

  if (authStatus === 'loading') {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <span className="loading loading-spinner loading-lg text-primary" />
      </main>
    )
  }

  if (authStatus === 'unauthenticated') {
    return (
      <main className="min-h-screen flex items-center justify-center p-6">
        <div className="card w-full max-w-md bg-base-200 border border-base-300 shadow-xl">
          <div className="card-body text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary text-primary-content text-2xl font-bold mb-4 mx-auto">
              🎧
            </div>
            <h2 className="font-display text-xl font-bold mb-2">You're invited!</h2>
            <p className="text-base-content/70 mb-4">
              Sign in with Spotify to join room{' '}
              <span className="font-mono font-bold brand-accent">{safeRoomCode}</span>
            </p>
            <button
              className="btn btn-primary btn-lg"
              onClick={() => loginWithSpotify(`/join/${safeRoomCode}`)}
            >
              Sign in with Spotify
            </button>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="card w-full max-w-md bg-base-200 border border-base-300 shadow-xl">
        <div className="card-body text-center">
          {error ? (
            <>
              <h2 className="font-display text-xl font-bold mb-2">Couldn't join room</h2>
              <p className="text-error text-sm mb-4">{error}</p>
              <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>
                Go to Dashboard
              </button>
            </>
          ) : (
            <>
              <span className="loading loading-spinner loading-lg text-primary mb-4" />
              <p className="text-base-content/70">
                Joining room <span className="font-mono font-bold brand-accent">{safeRoomCode}</span>...
              </p>
            </>
          )}
        </div>
      </div>
    </main>
  )
}

export default JoinRoomPage
