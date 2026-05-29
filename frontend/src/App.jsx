import { useEffect, useRef, useState } from "react";

import { fetchChats, fetchMessages, sendMessage, WS_URL } from "./api";

function App() {
  const [chats, setChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const selectedChatIdRef = useRef(null);

  useEffect(() => {
    selectedChatIdRef.current = selectedChatId;
  }, [selectedChatId]);

  useEffect(() => {
    let isMounted = true;

    async function loadChats() {
      try {
        const nextChats = await fetchChats();
        if (!isMounted) return;

        setChats(nextChats);
        if (!selectedChatIdRef.current && nextChats.length > 0) {
          setSelectedChatId(nextChats[0].id);
        }
      } catch {
        setError("Не удалось загрузить чаты");
      }
    }

    loadChats();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedChatId) {
      setMessages([]);
      return;
    }

    let isMounted = true;
    setIsLoadingMessages(true);

    async function loadMessages() {
      try {
        const nextMessages = await fetchMessages(selectedChatId);
        if (isMounted) {
          setMessages(nextMessages);
        }
      } catch {
        setError("Не удалось загрузить сообщения");
      } finally {
        if (isMounted) {
          setIsLoadingMessages(false);
        }
      }
    }

    loadMessages();
    return () => {
      isMounted = false;
    };
  }, [selectedChatId]);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);

    socket.onopen = () => setIsConnected(true);
    socket.onclose = () => setIsConnected(false);
    socket.onerror = () => setIsConnected(false);
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.event !== "message_created") {
        return;
      }

      const { chat, message } = data.payload;
      setChats((currentChats) => upsertChat(currentChats, chat));

      if (selectedChatIdRef.current === message.chat_id) {
        setMessages((currentMessages) => appendMessage(currentMessages, message));
      }
    };

    return () => socket.close();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    const text = draft.trim();

    if (!selectedChatId || !text) {
      return;
    }

    setError("");
    try {
      const message = await sendMessage(selectedChatId, text);
      setDraft("");
      setMessages((currentMessages) => appendMessage(currentMessages, message));
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(detail || "Не удалось отправить сообщение");
    }
  }

  const selectedChat = chats.find((chat) => chat.id === selectedChatId);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div>
            <span className="eyebrow">MVP SaaS CRM</span>
            <h1>Telegram CRM</h1>
          </div>
          <span className={isConnected ? "status online" : "status"} />
        </div>

        <div className="chat-list">
          {chats.length === 0 ? (
            <div className="empty-state">Ожидаем первое сообщение из Telegram</div>
          ) : (
            chats.map((chat) => (
              <button
                className={chat.id === selectedChatId ? "chat-item active" : "chat-item"}
                key={chat.id}
                onClick={() => setSelectedChatId(chat.id)}
                type="button"
              >
                <span className="chat-title">{chat.title || `Chat ${chat.telegram_chat_id}`}</span>
                <span className="chat-preview">{chat.last_message?.text || "Нет сообщений"}</span>
              </button>
            ))
          )}
        </div>
      </aside>

      <section className="conversation">
        <header className="conversation-header">
          <div>
            <span className="eyebrow">Диалог</span>
            <h2>{selectedChat?.title || "Выберите чат"}</h2>
          </div>
          {selectedChat && <span className="chat-id">tg:{selectedChat.telegram_chat_id}</span>}
        </header>

        {error && <div className="error-banner">{error}</div>}

        <div className="message-list">
          {isLoadingMessages ? (
            <div className="empty-state">Загружаем сообщения...</div>
          ) : messages.length === 0 ? (
            <div className="empty-state">Сообщения появятся здесь</div>
          ) : (
            messages.map((message) => (
              <div className={`message ${message.direction}`} key={message.id}>
                <p>{message.text}</p>
                <time>{formatTime(message.created_at)}</time>
              </div>
            ))
          )}
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <input
            disabled={!selectedChatId}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Напишите ответ клиенту..."
            value={draft}
          />
          <button disabled={!selectedChatId || !draft.trim()} type="submit">
            Отправить
          </button>
        </form>
      </section>
    </main>
  );
}

function upsertChat(chats, nextChat) {
  return [nextChat, ...chats.filter((chat) => chat.id !== nextChat.id)];
}

function appendMessage(messages, nextMessage) {
  if (messages.some((message) => message.id === nextMessage.id)) {
    return messages;
  }
  return [...messages, nextMessage];
}

function formatTime(value) {
  return new Intl.DateTimeFormat("ru", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default App;
