import {
  Building2,
  Inbox,
  LayoutDashboard,
  LogOut,
  Package,
  ShoppingBag,
} from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import LogoOEV from './LogoOEV.jsx'
import ThemeToggle from './ThemeToggle.jsx'

const NAV = [
  { to: '/', label: 'Tableau de bord', icon: LayoutDashboard, end: true },
  { to: '/commandes', label: 'Commandes', icon: ShoppingBag },
  { to: '/messages', label: 'Boite de reception', icon: Inbox },
  { to: '/catalogue', label: 'Catalogue', icon: Package },
]

export default function Sidebar({ unread = 0 }) {
  const { tenant, logout } = useAuth()
  const navigate = useNavigate()

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
      isActive
        ? 'bg-brand-500/12 text-brand-700 dark:bg-brand-500/20 dark:text-brand-300'
        : 'text-ink-600 hover:bg-paper-100 dark:text-paper-300 dark:hover:bg-ink-700'
    }`

  const signOut = () => {
    logout()
    navigate('/connexion', { replace: true })
  }

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-paper-200 bg-white px-3 py-4 dark:border-ink-700 dark:bg-ink-800">
      <div className="px-2 pb-5">
        <LogoOEV size={34} withWordmark />
      </div>

      <nav className="flex-1 space-y-1">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={linkClass}>
            <Icon size={17} />
            <span className="flex-1">{label}</span>
            {to === '/messages' && unread > 0 && (
              <span className="rounded-full bg-saffron-500 px-1.5 py-0.5 text-[11px] font-semibold text-white">
                {unread}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="space-y-2 border-t border-paper-200 pt-3 dark:border-ink-700">
        <div className="flex items-center justify-between px-3 py-1">
          <span className="text-xs text-ink-500 dark:text-paper-300">Apparence</span>
          <ThemeToggle compact />
        </div>

        {/* Profil d entreprise : juste au-dessus de la deconnexion */}
        <NavLink to="/profil" className={linkClass}>
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/15 text-brand-700 dark:text-brand-300">
            <Building2 size={15} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium">
              {tenant?.company_name || 'Mon entreprise'}
            </span>
            <span className="block truncate text-xs text-ink-500 dark:text-paper-300">
              {tenant?.sector || 'Profil'}
            </span>
          </span>
        </NavLink>

        <button
          type="button"
          onClick={signOut}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"
        >
          <LogOut size={17} />
          Se deconnecter
        </button>
      </div>
    </aside>
  )
}
