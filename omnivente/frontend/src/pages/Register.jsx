import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import LogoOEV from '../components/LogoOEV.jsx'
import ThemeToggle from '../components/ThemeToggle.jsx'
import { SECTORS } from '../components/constants.js'
import { useAuth } from '../context/AuthContext.jsx'

const EMPTY = {
  company_name: '',
  sector: SECTORS[0],
  description: '',
  address: '',
  district: '',
  city: '',
  email: '',
  phone: '',
  currency: 'FCFA',
  password: '',
}

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await register(form)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto w-full max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <LogoOEV size={38} withWordmark />
          <ThemeToggle compact />
        </div>

        <div className="card p-6 lg:p-8">
          <h1 className="font-display text-3xl font-bold">Creer votre espace entreprise</h1>
          <p className="mt-2 max-w-xl text-sm text-ink-500 dark:text-paper-300">
            Ces informations nourrissent votre agent de vente : il les utilise pour repondre a vos
            clients sur WhatsApp, Instagram, Messenger et par email.
          </p>

          <form onSubmit={submit} className="mt-7 grid gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="label" htmlFor="company_name">Nom de l entreprise</label>
              <input id="company_name" required className="field" value={form.company_name} onChange={update('company_name')} />
            </div>

            <div>
              <label className="label" htmlFor="sector">Secteur d activite</label>
              <select id="sector" className="field" value={form.sector} onChange={update('sector')}>
                {SECTORS.map((sector) => (
                  <option key={sector} value={sector}>{sector}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="label" htmlFor="currency">Devise</label>
              <input id="currency" className="field" value={form.currency} onChange={update('currency')} placeholder="FCFA" />
            </div>

            <div className="md:col-span-2">
              <label className="label" htmlFor="description">Description complete de l activite</label>
              <textarea
                id="description"
                rows={4}
                className="field"
                value={form.description}
                onChange={update('description')}
                placeholder="Ce que vous vendez, a qui, vos horaires, vos zones de livraison…"
              />
            </div>

            <div className="md:col-span-2">
              <label className="label" htmlFor="address">Adresse</label>
              <input id="address" className="field" value={form.address} onChange={update('address')} />
            </div>

            <div>
              <label className="label" htmlFor="district">Quartier</label>
              <input id="district" className="field" value={form.district} onChange={update('district')} />
            </div>

            <div>
              <label className="label" htmlFor="city">Ville</label>
              <input id="city" className="field" value={form.city} onChange={update('city')} />
            </div>

            <div>
              <label className="label" htmlFor="email">Email professionnel</label>
              <input id="email" type="email" required className="field" value={form.email} onChange={update('email')} />
            </div>

            <div>
              <label className="label" htmlFor="phone">Telephone pro</label>
              <input id="phone" className="field" value={form.phone} onChange={update('phone')} placeholder="228 90 00 00 00" />
            </div>

            <div className="md:col-span-2">
              <label className="label" htmlFor="password">Mot de passe (6 caracteres minimum)</label>
              <input
                id="password"
                type="password"
                required
                minLength={6}
                autoComplete="new-password"
                className="field"
                value={form.password}
                onChange={update('password')}
              />
            </div>

            {error && (
              <p className="md:col-span-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
                {error}
              </p>
            )}

            <div className="md:col-span-2 flex flex-wrap items-center gap-4">
              <button type="submit" className="btn-primary" disabled={busy}>
                {busy ? 'Creation…' : 'Creer mon espace'}
              </button>
              <Link to="/connexion" className="text-sm text-ink-500 hover:underline dark:text-paper-300">
                J ai deja un compte
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
