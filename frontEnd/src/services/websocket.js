let socket = null;

export const connectWebSocket = (onMessage, onOpen, onError, onClose, preferences) => {
  socket = new WebSocket("ws://20.244.6.45:8000");
  // socket = new WebSocket("ws://127.0.0.1:8000");
  socket.binaryType = "blob";

  socket.onopen = () => {
    console.log("WebSocket connected");
    if (preferences) {
      socket.send(JSON.stringify(preferences));
      console.log("Preferences sent:", preferences);
    }
    onOpen && onOpen();
  };

  socket.onmessage = (event) => {
    onMessage(event);
  };

  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
    onError && onError(err);
  };

  socket.onclose = () => {
    console.log("WebSocket closed");
    onClose && onClose();
  };
};

export const sendMessage = (message) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(message);
  } else {
    console.warn("WebSocket is not open");
  }
};

export const closeWebSocket = () => {
  if (socket) {
    socket.close();
  }
};