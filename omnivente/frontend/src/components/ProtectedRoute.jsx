import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import LogoOEV from './LogoOEV.jsx'

export default function ProtectedRoute({ children }) {
  const { tenant, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-rise text-center">
          <LogoOEV size={44} />
          <p className="mt-3 text-sm text-ink-500 dark:text-paper-300">Chargement de votre espace…</p>
        </div>
      </div>
    )
  }

  if (!tenant) {
    return <Navigate to="/connexion" state={{ from: location.pathname }} replace />
  }

  return children
}
