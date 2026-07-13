import { createContext, useContext, useState, ReactNode } from 'react'

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface WidgetContext {
  dashboard: string
  widgetTitle: string
  widgetType: 'grafico' | 'tabla' | 'kpi' | 'mapa'
  filters?: Record<string, any>
  data?: any
}

interface ChatContextType {
  open: boolean
  widget: WidgetContext | null
  messages: ChatMessage[]
  loading: boolean
  openChat: (widget: WidgetContext) => void
  closeChat: () => void
  toggleChat: () => void
  addMessage: (message: ChatMessage) => void
  clearMessages: () => void
  setLoading: (loading: boolean) => void
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

export function ChatProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [widget, setWidget] = useState<WidgetContext | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)

  const openChat = (w: WidgetContext) => {
    setWidget(w)
    setOpen(true)
  }

  const closeChat = () => {
    setOpen(false)
  }

  const toggleChat = () => {
    setOpen((prev) => !prev)
  }

  const addMessage = (message: ChatMessage) => {
    setMessages((prev) => [...prev, message])
  }

  const clearMessages = () => {
    setMessages([])
  }

  return (
    <ChatContext.Provider
      value={{
        open,
        widget,
        messages,
        loading,
        openChat,
        closeChat,
        toggleChat,
        addMessage,
        clearMessages,
        setLoading,
      }}
    >
      {children}
    </ChatContext.Provider>
  )
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used within ChatProvider')
  return ctx
}

export default ChatContext
