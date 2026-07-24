import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch, logout } from './api/client'
import {RoomViewer} from './components/RoomViewer'
function Dashboard() {
  const navigate = useNavigate()
  const [spotifyId, setSpotifyId] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [profileImage, setProfileImage] = useState('')
  const [userId, setUserId] = useState(null)

  useEffect(() => {
    let isMounted = true

    apiFetch('/user/auth/session')
      .then((session) => {
        if (isMounted) {
          const user = session?.user || {}
          setSpotifyId(user.spotify_id || '')
          setDisplayName(user.username || user.display_name || user.spotify_id || '')
          setProfileImage(user.profile_image || '')
          setUserId(user.id ?? null)
        }
      })
      .catch(() => {
        if (isMounted) {
          setSpotifyId('')
          setDisplayName('')
          setProfileImage('')
          setUserId(null)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  async function handleSignOut() {
    await logout()
    navigate('/', { replace: true })
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      <header className="flex items-center justify-between gap-2 rounded-box border border-base-300 bg-base-200 px-3 sm:px-5 py-3 sm:py-4">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-content text-sm font-bold hidden sm:flex shrink-0">
            🎧
          </div>
          <span className="font-display font-semibold hidden sm:inline shrink-0">Soundmates</span>
          <div className="divider divider-horizontal hidden sm:flex mx-1" />
          <div className="avatar shrink-0">
            <div className="w-10 rounded-full">
              {profileImage ? (
                <img src={profileImage} alt={displayName || spotifyId || 'User'} />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-primary text-primary-content font-semibold">
                  {(displayName || spotifyId || 'U').charAt(0).toUpperCase()}
                </div>
              )}
            </div>
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-sm truncate">{displayName || spotifyId || 'Dashboard'}</p>
            <p className="text-xs text-base-content/60 truncate">{spotifyId ? `@${spotifyId}` : 'Signed in'}</p>
          </div>
        </div>

        <button type="button" className="btn btn-outline btn-sm shrink-0" onClick={handleSignOut}>
          Log out
        </button>
      </header>

      <RoomViewer currentUserId={userId} />
    </main>
  )
}

export default Dashboard