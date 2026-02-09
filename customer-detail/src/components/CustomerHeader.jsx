import { User, Award } from 'lucide-react'
import ScoreCard from './ScoreCard'

export default function CustomerHeader({ customer, scores }) {
  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 py-5">
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
              <User className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">{customer.name}</h1>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Award className="w-4 h-4 text-amber-500" />
                <span className="font-medium text-amber-600">{customer.grade}</span>
                <span>·</span>
                <span>{customer.id}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <ScoreCard
            label="수익성"
            value={scores.profitability}
            max={100}
            color="blue"
            suffix="점"
          />
          <ScoreCard
            label="건전성"
            value={scores.soundness}
            max={100}
            color="green"
            suffix="점"
          />
          <ScoreCard
            label="리스크"
            value={scores.risk}
            max={100}
            color="red"
            suffix="점"
          />
        </div>
      </div>
    </header>
  )
}
