import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useRef } from 'react'
import { CHANNELS, STATUS_MAP, formatDate, formatMoney } from './constants.js'

// Une bande horizontale par statut : les commandes defilent lateralement.
export default function OrderSwimlane({ lane, currency, onStatusChange }) {
  const trackRef = useRef(null)
  const meta = STATUS_MAP[lane.status] || STATUS_MAP.a_preparer

  const scrollBy = (offset) => {
    trackRef.current?.scrollBy({ left: offset, behavior: 'smooth' })
  }

  return (
    <section className="card p-4">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className={`h-2.5 w-2.5 rounded-full ${meta.dot}`} />
          <h3 className="font-display text-base font-semibold">{lane.label}</h3>
          <span className="rounded-full bg-paper-100 px-2 py-0.5 text-xs font-medium text-ink-500 dark:bg-ink-700 dark:text-paper-300">
            {lane.count}
          </span>
        </div>
        {lane.count > 2 && (
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => scrollBy(-320)}
              className="rounded-md border border-paper-300 p-1 text-ink-500 transition hover:bg-paper-100 dark:border-ink-600 dark:hover:bg-ink-700"
              aria-label={`Faire defiler ${lane.label} vers la gauche`}
            >
              <ChevronLeft size={16} />
            </button>
            <button
              type="button"
              onClick={() => scrollBy(320)}
              className="rounded-md border border-paper-300 p-1 text-ink-500 transition hover:bg-paper-100 dark:border-ink-600 dark:hover:bg-ink-700"
              aria-label={`Faire defiler ${lane.label} vers la droite`}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}
      </header>

      {lane.count === 0 ? (
        <p className="rounded-lg border border-dashed border-paper-300 px-4 py-6 text-sm text-ink-500 dark:border-ink-600 dark:text-paper-300">
          Aucune commande dans cette bande. Les commandes creees par l agent apparaitront ici.
        </p>
      ) : (
        <div ref={trackRef} className="lane-scroll flex gap-3 overflow-x-auto pb-2">
          {lane.orders.map((order) => {
            const channel = CHANNELS[order.channel] || CHANNELS.whatsapp
            return (
              <article
                key={order.id}
                style={{ borderLeftColor: meta.accent }}
                className="w-[272px] shrink-0 rounded-lg border border-l-4 border-paper-200 bg-paper-50 p-3
                  dark:border-ink-600 dark:bg-ink-700"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium leading-tight">{order.customer_name || 'Client'}</p>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${channel.chip}`}
                  >
                    {channel.label}
                  </span>
                </div>

                <p className="mt-0.5 font-mono text-[11px] text-ink-500 dark:text-paper-300">
                  {order.reference}
                </p>

                <ul className="mt-2 space-y-0.5 text-sm text-ink-600 dark:text-paper-300">
                  {order.items.slice(0, 2).map((item) => (
                    <li key={item.id} className="truncate">
                      {item.quantity} x {item.product_name}
                    </li>
                  ))}
                  {order.items.length > 2 && (
                    <li className="text-xs">+ {order.items.length - 2} autre(s) article(s)</li>
                  )}
                </ul>

                <p className="mt-2 font-display text-lg font-semibold">
                  {formatMoney(order.total_amount, order.currency || currency)}
                </p>
                <p className="text-xs text-ink-500 dark:text-paper-300">
                  {formatDate(order.created_at)}
                </p>

                <label className="mt-3 block">
                  <span className="sr-only">Changer le statut de {order.reference}</span>
                  <select
                    value={order.status}
                    onChange={(event) => onStatusChange(order.id, event.target.value)}
                    className="field py-1.5 text-xs"
                  >
                    {Object.values(STATUS_MAP).map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
