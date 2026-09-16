import { useCallback, useEffect, useState } from 'react'
import api from '../api/client.js'
import OrderSwimlane from '../components/OrderSwimlane.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { ORDER_STATUSES } from '../components/constants.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function Orders() {
  const { tenant } = useAuth()
  const [lanes, setLanes] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      setLanes(await api.swimlanes())
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const changeStatus = async (orderId, status) => {
    // Mise a jour optimiste puis rechargement des bandes.
    setLanes((current) =>
      current.map((lane) => ({
        ...lane,
        orders: lane.orders.map((order) =>
          order.id === orderId ? { ...order, status } : order,
        ),
      })),
    )
    try {
      await api.updateOrderStatus(orderId, status)
    } catch (err) {
      setError(err.message)
    } finally {
      load()
    }
  }

  const total = lanes.reduce((sum, lane) => sum + lane.count, 0)

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold">Commandes</h1>
          <p className="mt-1 text-sm text-ink-500 dark:text-paper-300">
            {total} commande(s) reparties en bandes horizontales. Faites defiler chaque bande
            lateralement et changez le statut directement sur la carte.
          </p>
        </div>
        <button type="button" onClick={load} className="btn-ghost">
          Actualiser
        </button>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        {ORDER_STATUSES.map((status) => (
          <StatusBadge key={status.value} status={status.value} size="sm" />
        ))}
      </div>

      {error && (
        <p className="card border-red-200 p-3 text-sm text-red-700 dark:text-red-400">{error}</p>
      )}

      {loading ? (
        <p className="text-sm text-ink-500 dark:text-paper-300">Chargement des commandes…</p>
      ) : (
        <div className="space-y-4">
          {lanes.map((lane) => (
            <OrderSwimlane
              key={lane.status}
              lane={lane}
              currency={tenant?.currency || 'FCFA'}
              onStatusChange={changeStatus}
            />
          ))}
        </div>
      )}
    </div>
  )
}
