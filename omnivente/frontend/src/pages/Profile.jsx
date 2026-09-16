import { useEffect, useState } from 'react'
import api from '../api/client.js'
import { SECTORS } from '../components/constants.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function Profile() {
  const { tenant, setTenant } = useAuth()
  const [form, setForm] = useState(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (tenant) {
      setForm({
        company_name: tenant.company_name,
        sector: tenant.sector,
        description: tenant.description,
        address: tenant.address,
        district: tenant.district,
        city: tenant.city,
        phone: tenant.phone,
        currency: tenant.currency,
        whatsapp_phone_number_id: tenant.whatsapp_phone_number_id,
        meta_page_id: tenant.meta_page_id,
        smtp_user: tenant.smtp_user,
      })
    }
  }, [tenant])

  if (!form) return <p className="text-sm text-ink-500 dark:text-paper-300">Chargement du profil…</p>

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setStatus('')
    setError('')
    try {
      const updated = await api.updateProfile(form)
      setTenant(updated)
      setStatus('Modifications enregistrees.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="max-w-3xl space-y-5">
      <header>
        <h1 className="font-display text-3xl font-bold">Profil de l entreprise</h1>
        <p className="mt-1 text-sm text-ink-500 dark:text-paper-300">
          Ces informations alimentent les reponses de votre agent : adresse de retrait, ville de
          livraison, devise affichee aux clients.
        </p>
      </header>

      <form onSubmit={submit} className="card grid gap-4 p-6 md:grid-cols-2">
        <div className="md:col-span-2">
          <label className="label" htmlFor="company_name">Nom de l entreprise</label>
          <input id="company_name" className="field" value={form.company_name} onChange={update('company_name')} />
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
          <input id="currency" className="field" value={form.currency} onChange={update('currency')} />
        </div>

        <div className="md:col-span-2">
          <label className="label" htmlFor="description">Description de l activite</label>
          <textarea id="description" rows={4} className="field" value={form.description} onChange={update('description')} />
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
          <label className="label" htmlFor="phone">Telephone pro</label>
          <input id="phone" className="field" value={form.phone} onChange={update('phone')} />
        </div>

        <div>
          <label className="label">Email professionnel</label>
          <input className="field opacity-70" value={tenant.email} disabled />
        </div>

        <div className="md:col-span-2 border-t border-paper-200 pt-4 dark:border-ink-700">
          <h2 className="font-display text-lg font-semibold">Canaux connectes</h2>
          <p className="mt-1 text-sm text-ink-500 dark:text-paper-300">
            Les identifiants detailles se configurent dans GUIDE_CONFIGURATION_CANAUX.md.
          </p>
        </div>

        <div>
          <label className="label" htmlFor="whatsapp_phone_number_id">WhatsApp — Phone Number ID</label>
          <input id="whatsapp_phone_number_id" className="field" value={form.whatsapp_phone_number_id} onChange={update('whatsapp_phone_number_id')} />
        </div>

        <div>
          <label className="label" htmlFor="meta_page_id">Facebook / Instagram — Page ID</label>
          <input id="meta_page_id" className="field" value={form.meta_page_id} onChange={update('meta_page_id')} />
        </div>

        <div className="md:col-span-2">
          <label className="label" htmlFor="smtp_user">Email d envoi (SMTP)</label>
          <input id="smtp_user" className="field" value={form.smtp_user} onChange={update('smtp_user')} />
        </div>

        {status && <p className="md:col-span-2 text-sm text-brand-600 dark:text-brand-300">{status}</p>}
        {error && <p className="md:col-span-2 text-sm text-red-600 dark:text-red-400">{error}</p>}

        <div className="md:col-span-2">
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? 'Enregistrement…' : 'Enregistrer les modifications'}
          </button>
        </div>
      </form>

      <div className="card p-6">
        <h2 className="font-display text-lg font-semibold">Adresses de webhook</h2>
        <p className="mt-1 text-sm text-ink-500 dark:text-paper-300">
          Collez ces URL dans Meta Developers apres avoir expose votre serveur local.
        </p>
        <ul className="mt-3 space-y-1.5 font-mono text-xs text-ink-600 dark:text-paper-300">
          <li>POST /api/webhooks/whatsapp/{tenant.id}</li>
          <li>POST /api/webhooks/meta/{tenant.id}</li>
          <li>POST /api/webhooks/email/{tenant.id}</li>
        </ul>
      </div>
    </div>
  )
}
