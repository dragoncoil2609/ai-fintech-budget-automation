import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import './Chatbot.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const CHAT_SESSION_KEY = 'budgetbot.chatSessionId'
const INITIAL_MESSAGE = {
  role: 'assistant',
  text: 'Chào bạn! Mình là AI Money Coach. Bạn muốn hỏi gì về chi tiêu, hay muốn mình đề xuất và thiết lập ngân sách?',
}

function getChatSessionId() {
  try {
    const existing = window.localStorage.getItem(CHAT_SESSION_KEY)
    if (existing) return existing

    const next = window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`
    window.localStorage.setItem(CHAT_SESSION_KEY, next)
    return next
  } catch {
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`
  }
}

export default function Chatbot({ authFetch, month, resetKey }) {
  const [isOpen, setIsOpen] = useState(false)
  const [sessionId] = useState(getChatSessionId)
  const [messages, setMessages] = useState([INITIAL_MESSAGE])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    if (isOpen) {
      scrollToBottom()
    }
  }, [messages, isOpen])

  useEffect(() => {
    setMessages([INITIAL_MESSAGE])
    setInput('')
  }, [resetKey])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMsg = input.trim()
    setInput('')

    setMessages(prev => [...prev, { role: 'user', text: userMsg }, { role: 'assistant', text: '' }])
    setLoading(true)

    try {
      const res = await authFetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, session_id: sessionId, month: month || null }),
      })

      if (!res.ok) throw new Error('Failed to fetch from chat API')

      const reader = res.body.getReader()
      const decoder = new TextDecoder("utf-8")
      let done = false

      while (!done) {
        const { value, done: doneReading } = await reader.read()
        done = doneReading
        if (value) {
          const chunkStr = decoder.decode(value, { stream: true })
          const lines = chunkStr.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.text) {
                  setMessages(prev => {
                    const newMessages = [...prev]
                    newMessages[newMessages.length - 1].text += data.text
                    return newMessages
                  })
                }
              } catch (e) {
                console.error("Error parsing SSE JSON:", e)
              }
            }
          }
        }
      }
    } catch (err) {
      setMessages(prev => {
        const newMessages = [...prev]
        newMessages[newMessages.length - 1].text += `\n\nLỗi: ${err.message}`
        return newMessages
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* Floating Button */}
      <button 
        className={`chatbot-toggle ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="Chat với AI Money Coach"
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="chatbot-window">
          <div className="chatbot-header">
            <div className="chatbot-title">
              <div className="chatbot-avatar">🤖</div>
              AI Money Coach
            </div>
            <button className="chatbot-close" onClick={() => setIsOpen(false)}>✕</button>
          </div>
          
          <div className="chatbot-messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.role}`}>
                <div className="chat-bubble">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                  ) : (
                    msg.text.split('\n').map((line, i) => (
                      <span key={i}>
                        {line}
                        <br />
                      </span>
                    ))
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="chat-message assistant">
                <div className="chat-bubble typing">
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chatbot-input-area">
            <textarea
              className="chatbot-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Hỏi về chi tiêu..."
              rows={1}
            />
            <button 
              className="chatbot-send" 
              onClick={handleSend}
              disabled={loading || !input.trim()}
            >
              ➤
            </button>
          </div>
        </div>
      )}
    </>
  )
}
