import { Database } from 'lucide-react'

const ENTITIES = [
  { id: '고객', highlight: true },
  { id: '대출' },
  { id: '신용' },
  { id: '마이데이터' },
]

export default function MiniERDWidget() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <Database className="w-4 h-4" />
        연결 ERD 구조
      </h3>
      <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-4">
        {ENTITIES.map((entity, i) => (
          <div key={entity.id} className="flex items-center gap-2">
            <div
              className={`
                px-4 py-2 rounded-lg border-2 text-sm font-medium
                ${entity.highlight
                  ? 'bg-emerald-50 border-emerald-500 text-emerald-700 ring-2 ring-emerald-200'
                  : 'bg-gray-50 border-gray-200 text-gray-700'}
              `}
            >
              {entity.id}
            </div>
            {i < ENTITIES.length - 1 && (
              <svg width="24" height="16" viewBox="0 0 24 16" className="text-gray-300 shrink-0">
                <path d="M0 8 L18 8 M14 4 L18 8 L14 12" stroke="currentColor" strokeWidth="2" fill="none" />
              </svg>
            )}
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-500 mt-2 text-center">
        고객 → 대출 · 신용 · 마이데이터 연결 구조
      </p>
    </div>
  )
}
