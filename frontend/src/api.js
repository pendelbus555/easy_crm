import axios from "axios";

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";

export const api = axios.create({
  baseURL: API_URL,
});

export async function fetchChats() {
  const response = await api.get("/chats");
  return response.data;
}

export async function fetchMessages(chatId) {
  const response = await api.get(`/messages/${chatId}`);
  return response.data;
}

export async function sendMessage(chatId, text) {
  const response = await api.post("/send-message", { chat_id: chatId, text });
  return response.data.message;
}
