import { Bot, Send, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { CHANNELS, STAGE_LABELS, formatDate } from './constants.js'

// Fil de discussion : l arriere-plan change selon le canal du client.
export default function ChatBox({ conversation, onSend, onSimulate, sending }) {
  const [draft, setDraft] = useState('')
  const [simulation, setSimulation] = useState('')
  const [showSimulator, setShowSimulator] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [conversation?.messages?.length, conversation?.customer_id])

  if (!conversation) {
    return (
      <div className="card flex h-full items-center justify-center p-8 text-center">
        <div>
          <Sparkles className="mx-auto mb-3 text-brand-500" size={26} />
          <p className="font-display text-lg font-semibold">Choisissez une conversation</p>
          <p className="mt-1 text-sm text-ink-500 dark:text-paper-300">
            Les messages WhatsApp, Instagram, Messenger et email arrivent tous ici.
          </p>
        </div>
      </div>
    )
  }

  const channel = CHANNELS[conversation.channel] || CHANNELS.whatsapp

  const submit = async (event) => {
    event.preventDefault()
    const body = draft.trim()
    if (!body) return
    await onSend(body)
    setDraft('')
  }

  const simulate = async (event) => {
    event.preventDefault()
    const body = simulation.trim()
    if (!body) return
    await onSimulate(body)
    setSimulation('')
  }

  return (
    <div className="card flex h-full flex-col overflow-hidden">
      <header
        className="flex items-center justify-between gap-3 border-b border-paper-200 px-4 py-3 dark:border-ink-600"
        style={{ borderTop: `3px solid ${channel.color}` }}
      >
        <div>
          <p className="font-display text-base font-semibold">{conversation.full_name}</p>
          <p className="text-xs text-ink-500 dark:text-paper-300">
            {channel.label} · {STAGE_LABELS[conversation.stage] || conversation.stage}
          </p>
        </div>
        <button type="button" className="btn-ghost text-xs" onClick={() => setShowSimulator((v) => !v)}>
          <Bot size={14} />
          {showSimulator ? 'Masquer le test' : 'Tester l agent'}
        </button>
      </header>

      <div className={`flex-1 space-y-2 overflow-y-auto px-4 py-4 ${channel.surface}`}>
        {conversation.messages.length === 0 && (
          <p className="text-center text-sm text-ink-500">Aucun message pour l instant.</p>
        )}
        {conversation.messages.map((message) => {
          const outbound = message.direction === 'outbound'
          return (
            <div key={message.id} className={`flex ${outbound ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[78%] rounded-2xl px-3.5 py-2 text-sm shadow-sm ${
                  outbound ? channel.bubble : 'bg-white text-ink-800 dark:bg-ink-700 dark:text-paper-100'
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{message.body}</p>
                <p className="mt-1 flex items-center gap-1 text-[10px] opacity-60">
                  {message.is_bot && <Bot size={10} />}
                  {formatDate(message.created_at)}
                </p>
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      {showSimulator && (
        <form
          onSubmit={simulate}
          className="flex gap-2 border-t border-paper-200 bg-paper-50 px-4 py-2.5 dark:border-ink-600 dark:bg-ink-700"
        >
          <input
            value={simulation}
            onChange={(event) => setSimulation(event.target.value)}
            placeholder="Ecrire a la place du client pour voir la reponse de l agent"
            className="field"
          />
          <button type="submit" className="btn-ghost whitespace-nowrap text-xs">
            Envoyer comme client
          </button>
        </form>
      )}

      <form onSubmit={submit} className="flex gap-2 border-t border-paper-200 px-4 py-3 dark:border-ink-600">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={`Repondre sur ${channel.label}`}
          className="field"
        />
        <button type="submit" className="btn-primary" disabled={sending || !draft.trim()}>
          <Send size={15} />
          Envoyer
        </button>
      </form>
    </div>
  )
}
