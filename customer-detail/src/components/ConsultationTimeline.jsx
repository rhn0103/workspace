import { MessageSquare, Clock } from 'lucide-react'

export default function ConsultationTimeline({ items }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 h-full min-h-[320px]">
      <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
        <MessageSquare className="w-4 h-4" />
        상담 이력
      </h3>
      <div className="relative">
        <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-gray-200" />
        <ul className="space-y-0">
          {items.map((item, i) => (
            <li key={item.id} className="relative pl-8 pb-4">
              <div className="absolute left-0 w-6 h-6 rounded-full bg-emerald-100 border-2 border-white shadow flex items-center justify-center">
                <span className="text-[10px] font-bold text-emerald-700">{i + 1}</span>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                  <Clock className="w-3.5 h-3.5" />
                  {item.date}
                  <span className="px-1.5 py-0.5 rounded bg-gray-200 text-gray-600">{item.type}</span>
                </div>
                <div className="font-medium text-gray-800 text-sm">{item.title}</div>
                <p className="text-xs text-gray-600 mt-1 leading-relaxed">{item.memo}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
