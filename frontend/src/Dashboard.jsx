import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch, logout } from './api/client'
import {RoomViewer} from './components/RoomViewer'
function Dashboard() {
  const navigate = useNavigate()
  const [spotifyId, setSpotifyId] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [profileImage, setProfileImage] = useState('')

  useEffect(() => {
    let isMounted = true

    apiFetch('/user/auth/session')
      .then((session) => {
        if (isMounted) {
          const user = session?.user || {}
          setSpotifyId(user.spotify_id || '')
          setDisplayName(user.username || user.display_name || user.spotify_id || '')
          setProfileImage(user.profile_image || '')
        }
      })
      .catch(() => {
        if (isMounted) {
          setSpotifyId('')
          setDisplayName('')
          setProfileImage('')
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
    <main className="space-y-4">
      <header className="flex items-center justify-between rounded-xl border border-base-300 bg-base-200/70 px-4 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="avatar">
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
          <div>
            <p className="font-semibold">{displayName || spotifyId || 'Dashboard'}</p>
            <p className="text-sm text-base-content/60">{spotifyId ? `@${spotifyId}` : 'Signed in'}</p>
          </div>
        </div>

        <button type="button" className="btn btn-outline btn-sm" onClick={handleSignOut}>
          Log out
        </button>
      </header>

      <RoomViewer />
    </main>
  )
}

export default Dashboard