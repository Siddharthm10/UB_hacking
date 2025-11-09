import { io } from 'socket.io-client';

const socketUrl = typeof __SOCKET_URL__ !== 'undefined' ? __SOCKET_URL__ : 'http://localhost:8000';
let socket;

export function getAiSocket() {
  if (!socket) {
    socket = io(`${socketUrl}/ws/ai`, {
      path: '/socket.io',
      transports: ['websocket'],
      autoConnect: false
    });
  }
  if (!socket.connected) {
    socket.connect();
  }
  return socket;
}
