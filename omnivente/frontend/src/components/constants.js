// Reference unique des statuts et canaux. `accent` est applique en style inline
// (liseré gauche des cartes de commande).
// Reference unique des statuts et canaux. Modifiez les classes ici pour
// changer les couleurs des badges et des chatbox partout dans l'application.

export const ORDER_STATUSES = [
  {
    value: 'a_preparer',
    label: 'A preparer',
    badge:
      'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:border-amber-500/30',
    dot: 'bg-amber-500',
    accent: '#F59E0B',
  },
  {
    value: 'en_livraison',
    label: 'En cours de livraison',
    badge:
      'bg-cyan-100 text-cyan-800 border-cyan-200 dark:bg-cyan-500/15 dark:text-cyan-300 dark:border-cyan-500/30',
    dot: 'bg-cyan-500',
    accent: '#06B6D4',
  },
  {
    value: 'retrait_boutique',
    label: 'Retrait en boutique',
    badge:
      'bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:border-indigo-500/30',
    dot: 'bg-indigo-500',
    accent: '#6366F1',
  },
  {
    value: 'termine',
    label: 'Termine',
    badge:
      'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:border-emerald-500/30',
    dot: 'bg-emerald-500',
    accent: '#10B981',
  },
  {
    value: 'annule',
    label: 'Annule / Probleme',
    badge:
      'bg-red-100 text-red-800 border-red-200 dark:bg-red-500/15 dark:text-red-300 dark:border-red-500/30',
    dot: 'bg-red-500',
    accent: '#EF4444',
  },
]

export const STATUS_MAP = Object.fromEntries(ORDER_STATUSES.map((s) => [s.value, s]))

export const CHANNELS = {
  whatsapp: {
    label: 'WhatsApp',
    color: '#25D366',
    surface: 'chat-whatsapp',
    chip: 'bg-[#25D366]/12 text-[#0F7A3D] dark:text-[#4ADE80]',
    bubble: 'bg-[#DCF8C6] text-ink-800 dark:bg-[#12452E] dark:text-paper-100',
  },
  instagram: {
    label: 'Instagram',
    color: '#E1306C',
    surface: 'chat-instagram',
    chip: 'bg-[#E1306C]/12 text-[#B12256] dark:text-[#F472B6]',
    bubble: 'bg-white text-ink-800 dark:bg-[#33163A] dark:text-paper-100',
  },
  messenger: {
    label: 'Messenger',
    color: '#0084FF',
    surface: 'chat-messenger',
    chip: 'bg-[#0084FF]/12 text-[#0060BF] dark:text-[#60A5FA]',
    bubble: 'bg-white text-ink-800 dark:bg-[#12263F] dark:text-paper-100',
  },
  email: {
    label: 'Email',
    color: '#64748B',
    surface: 'chat-email',
    chip: 'bg-[#64748B]/12 text-[#475569] dark:text-[#94A3B8]',
    bubble: 'bg-white text-ink-800 dark:bg-ink-700 dark:text-paper-100',
  },
}

export const SECTORS = [
  'Vente de marchandises',
  'Habillement',
  'Electronique',
  'Restauration',
  'Services',
]

export const STAGE_LABELS = {
  accueil: 'Accueil',
  decouverte: 'Decouverte du besoin',
  proposition: 'Proposition',
  negociation: 'Negociation',
  collecte_infos: 'Collecte des infos',
  confirmation: 'Confirmation',
  cloture: 'Cloture',
}

export function formatMoney(amount, currency = 'FCFA') {
  const value = Number(amount || 0)
  return `${value.toLocaleString('fr-FR', { maximumFractionDigits: 0 })} ${currency}`
}

export function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}
