const COLORS = {
  blue: 'bg-blue-500 border-blue-500 text-blue-600',
  green: 'bg-emerald-500 border-emerald-500 text-emerald-600',
  red: 'bg-red-500 border-red-500 text-red-600',
}

export default function ScoreCard({ label, value, max = 100, color = 'blue', suffix = '' }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  const barColor = color === 'blue' ? 'bg-blue-500' : color === 'green' ? 'bg-emerald-500' : 'bg-red-500'
  const textColor = color === 'blue' ? 'text-blue-600' : color === 'green' ? 'text-emerald-600' : 'text-red-600'
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50/50 p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-500 mb-1">{label}</div>
      <div className="flex items-baseline gap-2">
        <span className={`text-2xl font-bold ${textColor}`}>{value}</span>
        {suffix && <span className="text-sm text-gray-500">{suffix}</span>}
      </div>
      <div className="mt-2 h-2 w-full rounded-full bg-gray-200 overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
