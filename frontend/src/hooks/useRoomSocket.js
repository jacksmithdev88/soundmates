import { useEffect, useRef, useState } from "react";

const socketStore = new Map();
const roomStateStore = new Map();

function buildSocketUrl(roomId) {
  const configuredBase =
    import.meta.env.VITE_WS_BASE_URL || import.meta.env.VITE_API_BASE_URL || "";

  if (configuredBase) {
    const normalizedBase = configuredBase.replace(/\/$/, "");

    const wsBase = normalizedBase
      .replace(/^http:/, "ws:")
      .replace(/^https:/, "wss:");

    return `${wsBase}/rooms/ws/${encodeURIComponent(roomId)}`;
  }

  const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";

  return `${wsProtocol}://${window.location.host}/rooms/ws/${encodeURIComponent(
    roomId,
  )}`;
}

export function useRoomSocket(roomId) {
  const [messages, setMessages] = useState([]);

  const [players, setPlayers] = useState(() => {
    return roomStateStore.get(roomId) || [];
  });

  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");

  const socketRef = useRef(null);
  const pendingMessagesRef = useRef([]);

  useEffect(() => {
    if (!roomId) {
      setConnected(false);
      setMessages([]);
      setPlayers([]);
      return;
    }

    // Load cached players if they exist
    const cachedPlayers = roomStateStore.get(roomId);

    if (cachedPlayers) {
      setPlayers(cachedPlayers);
    }

    const socket =
      socketStore.get(roomId) || new WebSocket(buildSocketUrl(roomId));

    socketRef.current = socket;

    if (!socketStore.has(roomId)) {
      socketStore.set(roomId, socket);
    }

    const handleOpen = () => {
      console.log("WebSocket opened for room", roomId);

      setConnected(true);
      setError("");

      while (pendingMessagesRef.current.length > 0) {
        const payload = pendingMessagesRef.current.shift();

        socket.send(JSON.stringify(payload));
      }
    };

    const handleMessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        console.log("WebSocket message received", message);

        setMessages((prev) => [...prev, message]);

        switch (message.type) {
          case "room_state":
          case "players_update":
            console.log("Updating players:", message.players);

            if (message.players) {
              setPlayers(message.players);

              roomStateStore.set(roomId, message.players);
            }

            break;

          default:
            break;
        }
      } catch (error) {
        console.error("Invalid websocket message", error);
      }
    };

    const handleClose = () => {
      console.log("Websocket closed");

      socketStore.delete(roomId);

      roomStateStore.delete(roomId);

      if (socketRef.current === socket) {
        socketRef.current = null;
      }

      setConnected(false);
    };

    const handleError = () => {
      setError("Unable to connect to room updates");

      setConnected(false);
    };

    socket.addEventListener("open", handleOpen);

    socket.addEventListener("message", handleMessage);

    socket.addEventListener("close", handleClose);

    socket.addEventListener("error", handleError);

    setConnected(socket.readyState === WebSocket.OPEN);

    return () => {
      socket.removeEventListener("open", handleOpen);

      socket.removeEventListener("message", handleMessage);

      socket.removeEventListener("close", handleClose);

      socket.removeEventListener("error", handleError);

      if (socketRef.current === socket) {
        socketRef.current = null;
      }
    };
  }, [roomId]);

  function sendMessage(payload) {
    console.log("Sending websocket message", payload);

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(payload));

      return;
    }

    pendingMessagesRef.current.push(payload);
  }

  return {
    connected,
    error,
    messages,
    players,
    sendMessage,
  };
}
