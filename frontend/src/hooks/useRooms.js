import { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../api/client'

const STORAGE_KEY = 'soundmates_active_room_code'

function extractRoomCode(payload) {
  if (!payload) return ''

  return (
    payload.room_code ||
    payload.room_id ||
    payload.roomCode ||
    payload.room?.id ||
    payload.room?.room_id ||
    ''
  )
}

export function useRooms() {
  const [roomCode, setRoomCode] = useState('')
  const [isInRoom, setIsInRoom] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [roomState, setRoomState] = useState(null)
  const [orphanedRoomId, setOrphanedRoomId] = useState('')

  const createRoom = useCallback(async () => {
    if (isInRoom) {
      setError('You are already in a room')
      return false
    }

    setIsLoading(true)
    setError('')

    try {
      const data = await apiFetch('/rooms/create', { method: 'POST' })
      const nextRoomCode = extractRoomCode(data)

      setRoomCode(nextRoomCode)
      setIsInRoom(Boolean(nextRoomCode))
      setRoomState(data)

      if (nextRoomCode) {
        localStorage.setItem(STORAGE_KEY, nextRoomCode)
      }

      return data
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to create room'
      setError(message)
      return ''
    } finally {
      setIsLoading(false)
    }
  }, [isInRoom])

  const joinRoom = useCallback(async (code) => {
    if (!code) {
      setError('Please enter a room code')
      return false
    }

    setIsLoading(true)
    setError('')

    try {
      const data = await apiFetch(`/rooms/join/${encodeURIComponent(code)}`, {
        method: 'POST',
      })

      const nextRoomCode = extractRoomCode(data) || code.toUpperCase()
      setRoomCode(nextRoomCode)
      setIsInRoom(true)
      setRoomState(data)
      localStorage.setItem(STORAGE_KEY, nextRoomCode)

      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to join room'
      setError(message)
      localStorage.removeItem(STORAGE_KEY)
      return false
    } finally {
      setIsLoading(false)
    }
  }, [])

  const leaveRoom = useCallback(async () => {
    setIsLoading(true)
    setError('')

    try {
      await apiFetch('/rooms/leave', { method: 'POST' })
      setRoomCode('')
      setIsInRoom(false)
      setRoomState(null)
      setOrphanedRoomId('')
      localStorage.removeItem(STORAGE_KEY)
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to leave room'
      setError(message)
      return false
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Rejoin whatever room we were last in (e.g. returning from a finished game)
  // so the room's players and score carry over instead of being lost on navigation.
  // The server is the source of truth here: a dropped socket, refresh, or
  // cleared localStorage can leave the client thinking it's room-less while
  // the backend still counts it as a member (it's only evicted by an explicit
  // leave). So we check /rooms/me first rather than trusting localStorage alone.
  useEffect(() => {
    let cancelled = false

    apiFetch('/rooms/me')
      .then((data) => {
        if (cancelled) return

        const savedCode = localStorage.getItem(STORAGE_KEY)

        if (data?.room_id) {
          if (savedCode && savedCode.toUpperCase() === data.room_id.toUpperCase()) {
            joinRoom(savedCode)
          } else {
            setOrphanedRoomId(data.room_id)
          }
        } else if (savedCode) {
          localStorage.removeItem(STORAGE_KEY)
        }
      })
      .catch(() => {
        const savedCode = localStorage.getItem(STORAGE_KEY)
        if (savedCode) {
          joinRoom(savedCode)
        }
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    roomCode,
    setRoomCode,
    isInRoom,
    isLoading,
    error,
    roomState,
    orphanedRoomId,
    createRoom,
    joinRoom,
    leaveRoom,
  }
}
