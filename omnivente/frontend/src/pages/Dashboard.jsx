import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client.js'
import { CHANNELS, ORDER_STATUSES, formatMoney } from '../components/constants.js'
import { useAuth } from '../context/AuthContext.jsx'

function Metric({ label, value, hint }) {
  return (
    <div className="card p-4">
      <p className="text-sm text-ink-500 dark:text-paper-300">{label}</p>
      <p className="mt-1 font-display text-3xl font-bold leading-none">{value}</p>
      {hint && <p className="mt-1.5 text-xs text-ink-500 dark:text-paper-300">{hint}</p>}
    </div>
  )
}

export default function Dashboard() {
  const { tenant } = useAuth()
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.stats().then(setStats).catch((err) => setError(err.message))
  }, [])

  if (error) {
    return <p className="card p-5 text-sm text-red-600 dark:text-red-400">{error}</p>
  }

  if (!stats) {
    return <p className="text-sm text-ink-500 dark:text-paper-300">Chargement des indicateurs…</p>
  }

  const maxChannel = Math.max(1, ...Object.values(stats.by_channel))
  const currency = stats.currency || tenant?.currency || 'FCFA'

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold">Bonjour, {tenant?.company_name}</h1>
        <p className="mt-1 text-sm text-ink-500 dark:text-paper-300">
          Voici l activite de vos canaux de vente aujourd hui.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Chiffre d affaires" value={formatMoney(stats.revenue, currency)} hint="Commandes hors annulations" />
        <Metric label="Commandes en cours" value={stats.orders_open} hint={`${stats.orders_total} au total`} />
        <Metric label="Clients" value={stats.customers_total} hint="Tous canaux confondus" />
        <Metric label="Messages a traiter" value={stats.messages_unread} hint="Non lus dans la boite de reception" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card p-5">
          <h2 className="font-display text-lg font-semibold">Repartition des commandes</h2>
          <ul className="mt-4 space-y-3">
            {ORDER_STATUSES.map((status) => {
              const count = stats.by_status[status.value] || 0
              const width = stats.orders_total ? (count / stats.orders_total) * 100 : 0
              return (
                <li key={status.value}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${status.dot}`} />
                      {status.label}
                    </span>
                    <span className="font-medium">{count}</span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-paper-200 dark:bg-ink-700">
                    <div className={`h-full rounded-full ${status.dot}`} style={{ width: `${width}%` }} />
                  </div>
                </li>
              )
            })}
          </ul>
          <Link to="/commandes" className="mt-5 inline-block text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">
            Ouvrir les bandes de commandes
          </Link>
        </section>

        <section className="card p-5">
          <h2 className="font-display text-lg font-semibold">Commandes par canal</h2>
          {Object.keys(stats.by_channel).length === 0 ? (
            <p className="mt-4 text-sm text-ink-500 dark:text-paper-300">
              Aucune commande enregistree. Connectez un canal pour commencer a vendre.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {Object.entries(stats.by_channel).map(([key, count]) => {
                const channel = CHANNELS[key] || CHANNELS.whatsapp
                return (
                  <li key={key}>
                    <div className="flex items-center justify-between text-sm">
                      <span>{channel.label}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-paper-200 dark:bg-ink-700">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${(count / maxChannel) * 100}%`, backgroundColor: channel.color }}
                      />
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
          <Link to="/messages" className="mt-5 inline-block text-sm font-medium text-brand-600 hover:underline dark:text-brand-300">
            Voir la boite de reception
          </Link>
        </section>
      </div>
    </div>
  )
}
