import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRooms } from '../hooks/useRooms'
import { useRoomSocket } from '../hooks/useRoomSocket'

const GAME_MODES = [
  {
    value: 'Whats the song?',
    icon: '🎷',
    description: "In this game a random users library will be picked. There will be 15 songs, each with 5 clues. Each clue will be revealed after 5 seconds. The less clues you use, the more points you score!"
  },
  {
    value: 'Who Listened To This?',
    icon: '🕵️',
    description: "In this game we will be judging all of your spotify profiles. Each round a user will be selected at random. We will select a song they have recently listened too. Each round you vote on the user you think has this song on repeat!"
  },
  {
    value: "Guess who? (Playlist)",
    icon: '📋',
    description: "In this game we will be taking a look at your playlists. Each round will get harder, starting with playlist names and ending with only one song on the playlist. Your job is to vote for the player whose library contains this playlist!"

  },
  {
    value: 'Guess the Year',
    icon: '📅',
    description: "We'll play you a song from someone's library — can you guess what year it was released?"
  },
  {
    value: 'Guess the Artist',
    icon: '🎤',
    description: "Hear a song title, guess the artist! Wrong answers come from other players' top artists."
  },
  {
    value: 'Find a Song From the Year',
    icon: '🎯',
    description: "We'll give you a year. Search Spotify and pick any song released in that year. Score 5 points for a perfect match, losing 1 point for every year you're off."
  },
  {
    value: 'Playlist Vibes',
    icon: '🎶',
    description: "We'll play 3 songs from a mystery playlist — no name, no hints. Guess whose library it belongs to just from the vibe!"
  },
  {
    value: 'Cover Art Blur',
    icon: '🖼️',
    description: "An album cover slowly comes into focus. Guess the song before it fully sharpens — the blurrier it still is, the more points you score!"
  },
  {
    value: 'Taste Twins',
    icon: '👯',
    description: "We'll pick two players. Everyone guesses how many artists they actually have in common in their Top Artists. Closest guess wins — find out who's really got the same taste (and who's a total outlier)!"
  }
]

export function RoomViewer({ currentUserId = null }) {
  const navigate = useNavigate()
  const { roomCode, setRoomCode, isInRoom, isLoading, error, createRoom, joinRoom, leaveRoom, roomState, orphanedRoomId } = useRooms()
  const {connected, error: socketError, messages, players, hostId, sendMessage} = useRoomSocket(isInRoom ? roomCode : '')
  const [selectedGameMode, setSelectedGameMode] = useState(roomState?.game_mode || '')
  const [selectionMessage, setSelectionMessage] = useState('')
  const [questionCount, setQuestionCount] = useState(15)
  const [linkCopied, setLinkCopied] = useState(false)

  const selectedMode = GAME_MODES.find((mode) => mode.value === selectedGameMode)

  const visiblePlayers = players.length ? players : (roomState?.players || [])
  const effectiveHostId = hostId ?? roomState?.host?.id ?? null
  const isHost = currentUserId != null && effectiveHostId != null && currentUserId === effectiveHostId

  const rankedPlayers = visiblePlayers
    .slice()
    .sort((a, b) => (b.score || 0) - (a.score || 0))

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

  // The host triggers "start_game" over the socket, and the backend broadcasts
  // "game_started" to every connection in the room (host included). Navigate
  // off of that broadcast rather than only doing it locally for the host, so
  // every other player actually gets moved into the game instead of being
  // left behind in the room view.
  useEffect(() => {
    if (!messages.length || !roomCode) return

    const startedMessage = messages.find((message) => message?.type === 'game_started')
    if (startedMessage) {
      navigate(`/game/${roomCode}`)
    }
  }, [messages, roomCode, navigate])

  async function handleRoomCreation() {
    await createRoom()
  }

  async function handleJoinRoom() {
    await joinRoom(roomCode)
  }

  async function handleLeaveRoom() {
    await leaveRoom()
  }

  async function handleCopyInviteLink() {
    if (!roomCode) return

    const inviteLink = `${window.location.origin}/join/${roomCode}`

    try {
      await navigator.clipboard.writeText(inviteLink)
      setLinkCopied(true)
      setTimeout(() => setLinkCopied(false), 2000)
    } catch {
      window.prompt('Copy this invite link:', inviteLink)
    }
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

    sendMessage({
      type:'start_game',
      room_id: roomCode,
      game_mode:selectedGameMode,
      question_count: questionCount,
    })
  }

  if (!isInRoom) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center p-4">
        <div className="card w-full max-w-md bg-base-200 border border-base-300 shadow-xl">
          <div className="card-body">
            <div className="text-center">
              <h2 className="font-display text-xl font-bold mb-2">You are not in a room</h2>

              <p className="text-center text-base-content/70 mb-4">
                Join an existing room or create your own to get started.
              </p>

              {error ? <p className="text-error text-sm mb-4">{error}</p> : null}

              {orphanedRoomId ? (
                <div className="alert alert-warning mb-4 flex flex-col items-start gap-2 text-left">
                  <span>
                    You're still marked as a member of room{' '}
                    <span className="font-mono font-bold">{orphanedRoomId}</span> from a previous
                    session. Leave it before creating or joining a new one.
                  </span>
                  <button
                    className="btn btn-sm btn-warning"
                    onClick={handleLeaveRoom}
                    disabled={isLoading}
                  >
                    {isLoading ? 'Working...' : `Leave room ${orphanedRoomId}`}
                  </button>
                </div>
              ) : null}

              <div className="form-control justify-between">
                <label className="label">
                  <span className="label-text font-semibold">Room Code</span>
                </label>

                <input
                  type="text"
                  placeholder="e.g. ABC123"
                  className="input input-bordered input-lg text-center uppercase tracking-widest my-4"
                  value={roomCode}
                  onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
                  maxLength={6}
                />

                <button
                  className="btn btn-primary btn-lg w-full"
                  onClick={handleJoinRoom}
                  disabled={isLoading || Boolean(orphanedRoomId)}
                >
                  {isLoading ? 'Working...' : 'Join Room'}
                </button>
              </div>
            </div>

            <div className="divider my-6">OR</div>

            <button
              className="btn btn-secondary btn-lg w-full"
              onClick={handleRoomCreation}
              disabled={isLoading || Boolean(orphanedRoomId)}
            >
              {isLoading ? 'Working...' : 'Create Room'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-2 sm:p-4 max-w-6xl mx-auto">
      <div className="card bg-base-200 border border-base-300 shadow-2xl overflow-hidden">
        <div className="bg-gradient-to-r from-primary/20 via-base-200 to-secondary/10 border-b border-base-300 px-4 sm:px-6 py-4 sm:py-5 flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-widest text-base-content/50 mb-1">Room code</p>
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <span className="font-mono text-2xl sm:text-4xl font-bold tracking-[0.15em] sm:tracking-[0.3em] brand-accent break-all">
                {roomCode || 'ABC123'}
              </span>
              <span className={`badge ${connected ? 'badge-success' : 'badge-ghost'}`}>
                {connected ? 'Live' : 'Offline'}
              </span>
            </div>
            <p className="text-sm text-base-content/60 mt-1">
              Share this code — or the link below — so friends can join.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              className="btn btn-primary btn-sm"
              onClick={handleCopyInviteLink}
            >
              {linkCopied ? 'Link copied!' : 'Copy invite link'}
            </button>

            <button
              className="btn btn-error btn-sm"
              onClick={handleLeaveRoom}
              disabled={isLoading}
            >
              {isLoading ? 'Working...' : 'Leave Room'}
            </button>
          </div>
        </div>

        {error ? <p className="text-error text-sm px-4 sm:px-6 pt-4">{error}</p> : null}
        {socketError ? <p className="text-error text-sm px-4 sm:px-6 pt-2">{socketError}</p> : null}

        <div className="grid lg:grid-cols-5 gap-4 sm:gap-6 p-3 sm:p-6">
          <div className="lg:col-span-2">
            <h3 className="font-display font-semibold text-sm mb-2 flex items-center gap-2">
              Scoreboard <span className="badge badge-sm badge-ghost">{rankedPlayers.length || 1}</span>
            </h3>

            <div className="space-y-2">
              {rankedPlayers.length > 0 ? (
                rankedPlayers.map((player, index) => {
                  const displayName = player.display_name || player.name || player.spotify_id || 'Player'
                  const profileImage = player.profile_image || player.image_url || player.avatar_url || player.profile_image_url || null
                  const isPlayerHost = effectiveHostId != null && player.id === effectiveHostId
                  const initials = displayName
                    .split(' ')
                    .map((part) => part[0])
                    .join('')
                    .slice(0, 2)
                    .toUpperCase()

                  return (
                    <div
                      key={`${player.id || player.spotify_id || player.name || 'player'}-${index}`}
                      className={`rounded-lg px-3 py-2 flex items-center gap-3 border ${
                        index === 0 && (player.score || 0) > 0
                          ? 'bg-primary/10 border-primary/40'
                          : 'bg-base-100 border-base-300'
                      }`}
                    >
                      <span className="text-sm w-5 shrink-0 text-center opacity-70">
                        {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`}
                      </span>
                      <div className="avatar shrink-0">
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
                      <span className="truncate text-sm flex-1 min-w-0">{displayName}</span>
                      {isPlayerHost ? <span className="badge badge-xs badge-accent shrink-0">Host</span> : null}
                      <span className="font-display font-bold text-lg w-10 shrink-0 text-right">
                        {player.score || 0}
                      </span>
                    </div>
                  )
                })
              ) : (
                <p className="text-sm text-base-content/70">You are the only player in this room.</p>
              )}
            </div>
          </div>

          <div className="lg:col-span-3">
            {isHost ? (
              <>
                <h3 className="font-display font-semibold text-sm mb-2">Choose game mode</h3>
                <div className="grid sm:grid-cols-2 gap-2">
                  {GAME_MODES.map((mode) => {
                    const isSelected = selectedGameMode === mode.value

                    return (
                      <button
                        key={mode.value}
                        type="button"
                        className={`tile-hover flex items-center gap-3 rounded-lg border px-4 py-3 text-left ${
                          isSelected
                            ? 'border-primary bg-primary/10'
                            : 'border-base-300 bg-base-100 hover:border-primary/40'
                        }`}
                        onClick={() => handleGameModeSelect(mode.value)}
                      >
                        <span className="text-xl shrink-0">{mode.icon}</span>
                        <span className="font-medium text-sm min-w-0 break-words">{mode.value}</span>
                      </button>
                    )
                  })}
                </div>

                {selectedMode?.description ? (
                  <div className="mt-4 rounded-lg border border-base-300 bg-base-100 p-4 text-left text-sm pop-in">
                    <p className="font-display font-semibold flex items-center gap-2 min-w-0">
                      <span className="text-lg shrink-0">{selectedMode.icon}</span>
                      <span className="break-words">{selectedMode.value}</span>
                    </p>
                    <p className="mt-2 text-base-content/70 break-words">{selectedMode.description}</p>
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-base-content/60">Pick a mode to unlock Start Game.</p>
                )}
                {selectionMessage ? <p className="mt-2 text-sm text-warning">{selectionMessage}</p> : null}

                {selectedGameMode === 'Taste Twins' ? (
                  <div className="mt-4 rounded-lg border border-base-300 bg-base-100 px-4 py-3 text-sm text-base-content/70">
                    Rounds are fixed at one per unique pair of players —{' '}
                    <span className="font-semibold text-base-content">
                      {(visiblePlayers.length * (visiblePlayers.length - 1)) / 2 || 0} round
                      {(visiblePlayers.length * (visiblePlayers.length - 1)) / 2 === 1 ? '' : 's'}
                    </span>{' '}
                    with {visiblePlayers.length || 0} player{visiblePlayers.length === 1 ? '' : 's'} in the room.
                  </div>
                ) : (
                  <div className="mt-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:justify-between rounded-lg border border-base-300 bg-base-100 px-4 py-3">
                    <span className="text-sm font-medium">Number of questions</span>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min={5}
                        max={20}
                        value={questionCount}
                        onChange={(e) => setQuestionCount(Number(e.target.value))}
                        className="range range-primary range-sm w-full sm:w-32"
                      />
                      <span className="badge badge-primary w-10 shrink-0">{questionCount}</span>
                    </div>
                  </div>
                )}

                <button
                  className="btn btn-primary btn-lg w-full mt-4"
                  onClick={handleStartGame}
                  disabled={!selectedGameMode || isLoading}
                >
                  {selectedGameMode ? 'Start Game' : 'Select a game mode first'}
                </button>
              </>
            ) : (
              <div className="h-full flex items-center justify-center text-center py-10">
                <p className="text-sm text-base-content/60">
                  Waiting for the host to pick a game mode and start the game...
                </p>
              </div>
            )}

            {messages.length > 0 ? (
              <div className="text-left text-sm bg-base-100 p-3 rounded-lg mt-4 border border-base-300">
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
        </div>
      </div>
    </div>
  )
}
