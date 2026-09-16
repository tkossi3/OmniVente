import { STATUS_MAP } from './constants.js'

export default function StatusBadge({ status, size = 'md' }) {
  const meta = STATUS_MAP[status] || STATUS_MAP.a_preparer
  const padding = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${padding} ${meta.badge}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  )
}
