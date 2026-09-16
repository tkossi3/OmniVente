import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import LogoOEV from '../components/LogoOEV.jsx'
import ThemeToggle from '../components/ThemeToggle.jsx'
import { useAuth } from '../context/AuthContext.jsx'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(form)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-between">
          <LogoOEV size={38} withWordmark />
          <ThemeToggle compact />
        </div>

        <div className="card p-6">
          <h1 className="font-display text-2xl font-bold">Connexion</h1>
          <p className="mt-1 text-sm text-ink-500 dark:text-paper-300">
            Retrouvez vos conversations et vos commandes.
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="label" htmlFor="email">Email professionnel</label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                className="field"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="contact@votre-entreprise.tg"
              />
            </div>

            <div>
              <label className="label" htmlFor="password">Mot de passe</label>
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                className="field"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </div>

            {error && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
                {error}
              </p>
            )}

            <button type="submit" className="btn-primary w-full" disabled={busy}>
              {busy ? 'Connexion…' : 'Se connecter'}
            </button>
          </form>

          <p className="mt-5 text-sm text-ink-500 dark:text-paper-300">
            Pas encore de compte ?{' '}
            <Link to="/inscription" className="font-medium text-brand-600 hover:underline dark:text-brand-300">
              Inscrire mon entreprise
            </Link>
          </p>
        </div>

        <p className="mt-4 text-center text-xs text-ink-500 dark:text-paper-300">
          Compte de demonstration apres ingestion : contact@entreprise-d.tg / omnivente2026
        </p>
      </div>
    </div>
  )
}
