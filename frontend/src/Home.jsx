import { loginWithSpotify } from './api/client'

const MODES = [
  { icon: '🎧', label: 'Whats the song?' },
  { icon: '🕵️', label: 'Who Listened To This?' },
  { icon: '📋', label: 'Guess who? (Playlist)' },
  { icon: '📅', label: 'Guess the Year' },
  { icon: '🎤', label: 'Guess the Artist' },
  { icon: '🎯', label: 'Find a Song From the Year' },
  { icon: '🎶', label: 'Playlist Vibes' },
  { icon: '🖼️', label: 'Cover Art Blur' },
  { icon: '👯', label: 'Taste Twins' },
]

function HomePage() {
  function handleSignIn() {
    loginWithSpotify()
  }

  return (
    <main className="min-h-screen flex flex-col">
      <div className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="max-w-lg w-full text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary text-primary-content text-2xl font-bold mb-6">
            🎧
          </div>

          <h1 className="font-display text-4xl sm:text-5xl font-bold tracking-tight">
            Soundmates
          </h1>

          <p className="mt-4 text-base-content/70 text-lg">
            A party game built from your friends&apos; real Spotify data.
            Guess songs, judge tastes, and see who&apos;s really been on repeat.
          </p>

          <button
            className="btn btn-primary btn-lg mt-8 px-10"
            onClick={handleSignIn}
          >
            Sign in with Spotify
          </button>

          <div className="mt-14 text-left">
            <p className="text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-3">
              9 game modes
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
              {MODES.map((mode) => (
                <div
                  key={mode.label}
                  className="flex items-center gap-2 rounded-lg border border-base-300 bg-base-200 px-3 py-2 text-sm"
                >
                  <span className="text-base shrink-0">{mode.icon}</span>
                  <span className="text-base-content/80 min-w-0 break-words">{mode.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

export default HomePage
