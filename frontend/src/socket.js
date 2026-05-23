import { io } from "socket.io-client";

let socket = null;

export function getSocket() {
  if (!socket) {
    socket = io({
      path: "/socket.io",
      withCredentials: true,
      transports: ["websocket", "polling"],
    });
    socket.on("connect", () => socket.emit("join"));
  }
  return socket;
}
