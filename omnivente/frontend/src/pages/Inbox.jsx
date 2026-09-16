import { useCallback, useEffect, useState } from 'react'
import api from '../api/client.js'
import ChatBox from '../components/ChatBox.jsx'
import { CHANNELS, formatDate } from '../components/constants.js'

export default function Inbox() {
  const [conversations, setConversations] = useState([])
  const [active, setActive] = useState(null)
  const [conversation, setConversation] = useState(null)
  const [filter, setFilter] = useState('tous')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const loadList = useCallback(async () => {
    try {
      const data = await api.listConversations()
      setConversations(data)
      setActive((current) => current ?? data[0]?.customer_id ?? null)
    } catch (err) {
      setError(err.message)
    }
  }, [])

  const loadConversation = useCallback(async (customerId) => {
    if (!customerId) return
    try {
      setConversation(await api.conversation(customerId))
    } catch (err) {
      setError(err.message)
    }
  }, [])

  useEffect(() => {
    loadList()
  }, [loadList])

  useEffect(() => {
    loadConversation(active)
  }, [active, loadConversation])

  const send = async (body) => {
    setSending(true)
    try {
      await api.sendMessage({ customer_id: active, body, direction: 'outbound' })
      await loadConversation(active)
      await loadList()
    } catch (err) {
      setError(err.message)
    } finally {
      setSending(false)
    }
  }

  const simulate = async (body) => {
    if (!conversation) return
    const target = conversations.find((c) => c.customer_id === conversation.customer_id)
    try {
      await api.simulateIncoming({
        channel: conversation.channel,
        external_ref: target?.external_ref || String(conversation.customer_id),
        full_name: conversation.full_name,
        body,
      })
      await loadConversation(active)
      await loadList()
    } catch (err) {
      setError(err.message)
    }
  }

  const visible =
    filter === 'tous' ? conversations : conversations.filter((c) => c.channel === filter)

  return (
    <div className="flex h-full flex-col gap-4">
      <header>
        <h1 className="font-display text-3xl font-bold">Boite de reception</h1>
        <p className="mt-1 text-sm text-ink-500 dark:text-paper-300">
          Tous vos canaux dans un seul fil. L arriere-plan change selon la plateforme du client.
        </p>
      </header>

      {error && <p className="card p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="flex flex-wrap gap-2">
        {['tous', ...Object.keys(CHANNELS)].map((key) => {
          const isActive = filter === key
          const label = key === 'tous' ? 'Tous les canaux' : CHANNELS[key].label
          return (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                isActive
                  ? 'border-brand-500 bg-brand-500/12 text-brand-700 dark:text-brand-300'
                  : 'border-paper-300 text-ink-500 hover:bg-paper-100 dark:border-ink-600 dark:text-paper-300 dark:hover:bg-ink-700'
              }`}
            >
              {label}
            </button>
          )
        })}
      </div>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[320px_1fr]">
        <div className="card flex max-h-[70vh] flex-col overflow-y-auto">
          {visible.length === 0 && (
            <p className="p-5 text-sm text-ink-500 dark:text-paper-300">
              Aucune conversation sur ce canal pour l instant.
            </p>
          )}
          {visible.map((item) => {
            const channel = CHANNELS[item.channel] || CHANNELS.whatsapp
            const isActive = item.customer_id === active
            return (
              <button
                key={item.customer_id}
                type="button"
                onClick={() => setActive(item.customer_id)}
                className={`border-b border-paper-200 px-4 py-3 text-left transition last:border-b-0 dark:border-ink-700 ${
                  isActive ? 'bg-brand-500/8 dark:bg-brand-500/15' : 'hover:bg-paper-100 dark:hover:bg-ink-700'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 truncate font-medium">
                    <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: channel.color }} />
                    {item.full_name}
                  </span>
                  {item.unread > 0 && (
                    <span className="rounded-full bg-saffron-500 px-1.5 py-0.5 text-[11px] font-semibold text-white">
                      {item.unread}
                    </span>
                  )}
                </div>
                <p className="mt-1 truncate text-xs text-ink-500 dark:text-paper-300">
                  {item.last_message || 'Nouvelle conversation'}
                </p>
                <p className="mt-0.5 text-[11px] text-ink-500/80 dark:text-paper-300/70">
                  {channel.label} · {formatDate(item.last_message_at)}
                </p>
              </button>
            )
          })}
        </div>

        <div className="min-h-[520px]">
          <ChatBox
            conversation={conversation}
            onSend={send}
            onSimulate={simulate}
            sending={sending}
          />
        </div>
      </div>
    </div>
  )
}
