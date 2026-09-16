import { Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import api from '../api/client.js'
import LogoOEV from './LogoOEV.jsx'
import Sidebar from './Sidebar.jsx'
import ThemeToggle from './ThemeToggle.jsx'

export default function Layout() {
  const [unread, setUnread] = useState(0)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    let active = true
    api
      .stats()
      .then((data) => {
        if (active) setUnread(data.messages_unread)
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [location.pathname])

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="hidden lg:block">
        <Sidebar unread={unread} />
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div
            className="absolute inset-0 bg-ink-900/50"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div className="relative z-10">
            <Sidebar unread={unread} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-paper-200 bg-white px-4 py-3 dark:border-ink-700 dark:bg-ink-800 lg:hidden">
          <button
            type="button"
            onClick={() => setMobileOpen((v) => !v)}
            className="btn-ghost p-2"
            aria-label="Ouvrir le menu"
          >
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
          <LogoOEV size={28} withWordmark />
          <ThemeToggle compact />
        </header>

        <main className="flex-1 overflow-y-auto p-4 lg:p-7">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
