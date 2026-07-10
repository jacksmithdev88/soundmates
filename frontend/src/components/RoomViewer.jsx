import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRooms } from '../hooks/useRooms'
import { useRoomSocket } from '../hooks/useRoomSocket'

const GAME_MODES = [
  {
    value: 'Higher or Lower',
    emoji: '📈❓👍👎',
    description: "In this game we will be taking a peak at the charts! You will be shown two songs, all you have to do is cast your vote on whether the next song is higher or lower!"
  },
  {
    value: 'Whats the song?',
    emoji: '😌🪈🎷✨',
    description: "In this game a random users library will be picked. There will be 15 songs, each with 5 clues. Each clue will be revealed after 5 seconds. The less clues you use, the more points you score!"
  },
  {
    value: 'Who Listened To This?',
    emoji: '🎧🤫🫣👀',
    description: "In this game we will be judging all of your spotify profiles. Each round a user will be selected at random. We will select a song they have recently listened too. Each round you vote on the user you think has this song on repeat!"
  },
  {
    value: "Guess who? (Playlist)",
    emoji: "📋🤥⁉️🤐" ,
    description: "In this game we will be taking a look at your playlists. Each round will get harder, starting with playlist names and ending with only one song on the playlist. Your job is to vote for the player you think owns this playlist!"

  }
  

]

export function RoomViewer() {
  const navigate = useNavigate()
  const { roomCode, setRoomCode, isInRoom, isLoading, error, createRoom, joinRoom, leaveRoom, roomState } = useRooms()
  const {connected, error: socketError, messages, players, sendMessage} = useRoomSocket(isInRoom ? roomCode : '')
  const [selectedGameMode, setSelectedGameMode] = useState(roomState?.game_mode || '')
  const [selectionMessage, setSelectionMessage] = useState('')

  const selectedMode = GAME_MODES.find((mode) => mode.value === selectedGameMode)

  const visiblePlayers = roomState?.players?.length ? roomState.players : players
  const isHost = Boolean(roomState?.host) || players.some((player) => player.is_host) || players.some((player) => player.id === 1) || (players.length === 1 && connected)

  useEffect(() => {
    if (roomState?.game_mode) {
      setSelectedGameMode(roomState.game_mode)
    }
  }, [roomState?.game_mode])

  useEffect(() => {
    if (!messages.length) return

    const latestMessage = messages[messages.length - 1]
    if (latestMessage?.type === 'game_mode_selected' && latestMessage.game_mode) {
      setSelectedGameMode(latestMessage.game_mode)
      setSelectionMessage('')
    }
  }, [messages])

  async function handleRoomCreation() {
    await createRoom()
  }

  async function handleJoinRoom() {
    await joinRoom(roomCode)
  }

  async function handleLeaveRoom() {
    await leaveRoom()
  }

  function handleGameModeSelect(gameMode) {
    if (!roomCode) return

    setSelectedGameMode(gameMode)
    setSelectionMessage('')
    sendMessage({
      type: 'select_game_mode',
      room_code: roomCode,
      room_id: roomCode,
      game_mode: gameMode,
    })
  }

  function handleStartGame() {
    if (!roomCode) return

    if (!selectedGameMode) {
      setSelectionMessage('Please select a game mode before starting.')
      return
    }

    console.log('Start Game clicked for room', roomCode)
      sendMessage({
      type:'start_game',
      room_id: roomCode,
      game_mode:selectedGameMode
  })

  setTimeout(() => {
      navigate(`/game/${roomCode}`)
  }, 500)
  }

  return (
    <div className="flex min-h-[70vh] items-center justify-center p-6">
      <div className="card w-full max-w-lg bg-base-200 shadow-2xl">
        <div className="card-body">
            {isInRoom ? (
              <div className="text-center">
                <h2 className="text-2xl font-bold mb-4">You are in a room!</h2>
                <p className="text-center text-base-content/70 mb-4">
                    Share this room code with your friends to join: <span className="font-mono font-bold">{roomCode || 'ABC123'}</span>
                </p>

                {error ? <p className="text-error text-sm mb-4">{error}</p> : null}
                <p className={`text-sm mb-2 ${connected ? 'text-success' : 'text-base-content/70'}`}>
                  Live room connection: {connected ? 'connected' : 'disconnected'}
                </p>
                {socketError ? <p className="text-error text-sm mb-2">{socketError}</p> : null}
                {visiblePlayers.length > 0 ? (
                  <div className="mt-4 text-left">
                    <h3 className="font-semibold mb-2">Players</h3>
                    <ul className="space-y-2 text-sm">
                      {visiblePlayers.map((player, index) => {
                        const displayName = player.display_name || player.name || player.spotify_id || 'Player'
                        const profileImage = player.profile_image || player.image_url || player.avatar_url || player.profile_image_url || null
                        const initials = displayName
                          .split(' ')
                          .map((part) => part[0])
                          .join('')
                          .slice(0, 2)
                          .toUpperCase()

                        return (
                          <li key={`${player.id || player.spotify_id || player.name || 'player'}-${index}`} className="bg-base-100 rounded px-3 py-2 flex items-center gap-3">
                            <div className="avatar">
                              <div className="w-8 rounded-full">
                                {profileImage ? (
                                  <img src={profileImage} alt={displayName} />
                                ) : (
                                  <div className="flex h-full w-full items-center justify-center bg-primary text-primary-content text-xs font-semibold">
                                    {initials}
                                  </div>
                                )}
                              </div>
                            </div>
                            <span>{displayName}</span>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                ) : (
                  <div className="mt-4 text-left">
                    <h3 className="font-semibold mb-2">Players</h3>
                    <p className="text-sm text-base-content/70">You are the only player in this room.</p>
                  </div>
                )}

                {isHost ? (
                  <>
                    <div className="mt-4 text-left">
                      <h3 className="font-semibold mb-2">Choose game mode</h3>
                      <div className="grid gap-2">
                        {GAME_MODES.map((mode) => (
                          <button
                            key={mode.value}
                            type="button"
                            className={`btn btn-lg justify-start ${
                              selectedGameMode === mode.value ? 'btn-primary' : 'btn-outline'
                            }`}
                            onClick={() => handleGameModeSelect(mode.value)}
                          >
                            {mode.emoji} {mode.value}
                          </button>
                        ))}
                      </div>
                      <p className="mt-2 text-sm text-base-content/70">
                        {selectedGameMode ? `Selected: ${selectedGameMode}` : 'Pick a mode to unlock Start Game.'}
                      </p>
                      {selectedMode?.description ? (
                        <div className="mt-4 rounded-box border border-base-300 bg-base-100 p-4 text-left text-sm text-base-content">
                          <p className="font-semibold">Description</p>
                          <p className="mt-2">{selectedMode.description}</p>
                        </div>
                      ) : null}
                      {selectionMessage ? <p className="mt-2 text-sm text-warning">{selectionMessage}</p> : null}
                    </div>

                    <button className="btn btn-primary btn-lg w-full mt-4" onClick={handleStartGame} disabled={!selectedGameMode || isLoading}>
                      {selectedGameMode ? 'Start Game' : 'Select a game mode first'}
                    </button>
                  </>
                ) : null}

                {messages.length > 0 ? (
                  <div className="text-left text-sm bg-base-100 p-3 rounded mt-4">
                    {messages.slice(-3).map((message, index) => {
                      if (typeof message === 'string') {
                        return <div key={`msg-${index}`} className="mb-2 last:mb-0">{message}</div>
                      }

                      if (message?.type === 'connected') {
                        return <div key={`msg-${index}`} className="mb-2 last:mb-0">Connected to room {message.room_id || ''}</div>
                      }

                      if (message?.type === 'message') {
                        return <div key={`msg-${index}`} className="mb-2 last:mb-0">{message.text || 'New room update'}</div>
                      }

                      return <div key={`msg-${index}`} className="mb-2 last:mb-0">{message?.message || 'Room update received'}</div>
                    })}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="text-center">
                <h2 className="text-2xl font-bold mb-4">You are not in a room.</h2>

                <p className="text-center text-base-content/70 mb-4">
                    Join an existing room or create your own.
                </p>

                {error ? <p className="text-error text-sm mb-4">{error}</p> : null}

                <div className="form-control justify-between">
                    <label className="label">
                    <span className="label-text font-semibold">Room Code</span>
                    </label>

                    <input
                    type="text"
                    placeholder="e.g. ABC123"
                    className="input input-bordered input-lg text-center uppercase tracking-widest my-6"
                    value={roomCode}
                    onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
                    maxLength={6}
                    />

                    <button className="btn btn-primary btn-lg w-full" onClick={handleJoinRoom} disabled={isLoading}>
                    {isLoading ? 'Working...' : 'Join Room'}
                    </button>
                </div>
              </div>
            )}
                

          <div className="divider my-6">OR</div>

          <div className="grid grid-cols-2 gap-4">
            <button className="btn btn-secondary btn-lg" onClick={handleRoomCreation} disabled={isLoading || isInRoom}>
              {isLoading ? 'Working...' : isInRoom ? 'Already in room' : 'Create Room'}
            </button>

            <button className="btn btn-error btn-lg" onClick={handleLeaveRoom} disabled={isLoading}>
              {isLoading ? 'Working...' : 'Leave Room'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}