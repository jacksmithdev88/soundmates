import { useCallback, useState } from 'react'
import { apiFetch } from '../api/client'

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

      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to join room'
      setError(message)
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
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to leave room'
      setError(message)
      return false
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    roomCode,
    setRoomCode,
    isInRoom,
    isLoading,
    error,
    roomState,
    createRoom,
    joinRoom,
    leaveRoom,
  }
}
