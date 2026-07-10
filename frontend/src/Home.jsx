import { loginWithSpotify } from './api/client'

function HomePage() {

  function handleSignIn() {
    loginWithSpotify()
  }


  return (
    <main>
      <div className="hero bg-base-200 min-h-screen">
            <div className="hero-content text-center">
                <div className="max-w-md">
                <h1 className="text-5xl font-bold">Hello there</h1>
                <p className="py-6">
                    Are you ready to expose your Spotify listening habits to your friends? Click the button below to get started!
                </p>
                <button className="btn btn-primary" onClick={handleSignIn}>Sign in to Spotify</button>
                </div>
            </div>
        </div>
    </main>
  )
}

export default HomePage
