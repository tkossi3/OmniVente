import { Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import api from '../api/client.js'
import { formatMoney } from '../components/constants.js'
import { useAuth } from '../context/AuthContext.jsx'

const EMPTY = { name: '', category: '', description: '', price: '', stock: '', sku: '' }

export default function Products() {
  const { tenant } = useAuth()
  const [products, setProducts] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = async () => {
    try {
      setProducts(await api.listProducts())
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.createProduct({
        ...form,
        price: Number(form.price || 0),
        stock: Number(form.stock || 0),
        currency: tenant?.currency || 'FCFA',
      })
      setForm(EMPTY)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    try {
      await api.deleteProduct(id)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="font-display text-3xl font-bold">Catalogue</h1>
        <p className="mt-1 text-sm text-ink-500 dark:text-paper-300">
          Votre agent propose ces articles aux clients et calcule les totaux a partir de ces prix.
        </p>
      </header>

      {error && <p className="card p-3 text-sm text-red-600 dark:text-red-400">{error}</p>}

      <form onSubmit={submit} className="card grid gap-3 p-5 md:grid-cols-6">
        <div className="md:col-span-2">
          <label className="label" htmlFor="name">Article</label>
          <input id="name" required className="field" value={form.name} onChange={update('name')} />
        </div>
        <div>
          <label className="label" htmlFor="category">Categorie</label>
          <input id="category" className="field" value={form.category} onChange={update('category')} />
        </div>
        <div>
          <label className="label" htmlFor="price">Prix</label>
          <input id="price" type="number" min="0" className="field" value={form.price} onChange={update('price')} />
        </div>
        <div>
          <label className="label" htmlFor="stock">Stock</label>
          <input id="stock" type="number" min="0" className="field" value={form.stock} onChange={update('stock')} />
        </div>
        <div className="flex items-end">
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            <Plus size={15} />
            Ajouter
          </button>
        </div>
        <div className="md:col-span-6">
          <label className="label" htmlFor="description">Description</label>
          <input id="description" className="field" value={form.description} onChange={update('description')} />
        </div>
      </form>

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="border-b border-paper-200 text-left text-xs text-ink-500 dark:border-ink-700 dark:text-paper-300">
            <tr>
              <th className="px-4 py-3 font-medium">Article</th>
              <th className="px-4 py-3 font-medium">Categorie</th>
              <th className="px-4 py-3 font-medium">Prix</th>
              <th className="px-4 py-3 font-medium">Stock</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {products.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-ink-500 dark:text-paper-300">
                  Votre catalogue est vide. Ajoutez un premier article ci-dessus.
                </td>
              </tr>
            )}
            {products.map((product) => (
              <tr key={product.id} className="border-b border-paper-200 last:border-b-0 dark:border-ink-700">
                <td className="px-4 py-3">
                  <p className="font-medium">{product.name}</p>
                  <p className="text-xs text-ink-500 dark:text-paper-300">{product.description}</p>
                </td>
                <td className="px-4 py-3 text-ink-500 dark:text-paper-300">{product.category || '—'}</td>
                <td className="px-4 py-3 font-medium">{formatMoney(product.price, product.currency)}</td>
                <td className="px-4 py-3">
                  <span className={product.stock > 0 ? '' : 'text-red-600 dark:text-red-400'}>
                    {product.stock > 0 ? product.stock : 'Rupture'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => remove(product.id)}
                    className="rounded-md p-1.5 text-ink-500 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10"
                    aria-label={`Supprimer ${product.name}`}
                  >
                    <Trash2 size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
