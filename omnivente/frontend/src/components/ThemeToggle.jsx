import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../context/ThemeContext.jsx'

export default function ThemeToggle({ compact = false }) {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? 'Passer en mode clair' : 'Passer en mode sombre'}
      className={`group relative inline-flex items-center rounded-full border transition-colors duration-200
        ${isDark ? 'border-ink-600 bg-ink-700' : 'border-paper-300 bg-paper-100'}
        ${compact ? 'h-8 w-[58px]' : 'h-9 w-16'}`}
    >
      <span
        className={`absolute flex items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-200 ease-out
          dark:bg-ink-900
          ${compact ? 'h-6 w-6' : 'h-7 w-7'}
          ${isDark ? (compact ? 'translate-x-[27px]' : 'translate-x-[32px]') : 'translate-x-[3px]'}`}
      >
        {isDark ? (
          <Moon size={compact ? 13 : 15} className="text-saffron-400" />
        ) : (
          <Sun size={compact ? 13 : 15} className="text-saffron-500" />
        )}
      </span>
      <span className="sr-only">{isDark ? 'Mode sombre actif' : 'Mode clair actif'}</span>
    </button>
  )
}
