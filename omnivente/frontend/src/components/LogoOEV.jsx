// Logo OmniVente : monogramme OEV au coeur d'une bulle de discussion.
// Pour changer le logo, modifiez uniquement ce fichier.

export default function LogoOEV({ size = 36, withWordmark = false, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        role="img"
        aria-label="OmniVente"
        className="shrink-0"
      >
        <defs>
          <linearGradient id="oev-bubble" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#0E9C8A" />
            <stop offset="100%" stopColor="#085E55" />
          </linearGradient>
        </defs>
        <path
          d="M12 6h40a6 6 0 0 1 6 6v28a6 6 0 0 1-6 6H29.5L16 58V46h-4a6 6 0 0 1-6-6V12a6 6 0 0 1 6-6Z"
          fill="url(#oev-bubble)"
        />
        <text
          x="32"
          y="31"
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#FBFBFA"
          fontFamily="'Bricolage Grotesque', Georgia, serif"
          fontSize="19"
          fontWeight="700"
          letterSpacing="0.5"
        >
          OEV
        </text>
        <circle cx="22" cy="40" r="2" fill="#F5B942" />
        <circle cx="32" cy="40" r="2" fill="#F5B942" opacity="0.75" />
        <circle cx="42" cy="40" r="2" fill="#F5B942" opacity="0.5" />
      </svg>
      {withWordmark && (
        <span className="font-display text-xl font-bold tracking-tight text-ink-800 dark:text-paper-50">
          OmniVente
        </span>
      )}
    </span>
  )
}
