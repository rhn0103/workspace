import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

export default function LoanCreditChart({ loanData, creditData }) {
  const data = loanData.map((l, i) => ({
    month: l.month,
    대출잔액: l.balance,
    신용점수: creditData[i]?.score ?? 0,
  }))

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 h-[320px]">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">대출 잔액 & 신용 점수 추이</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#6b7280" />
          <YAxis yAxisId="left" tick={{ fontSize: 11 }} stroke="#3182CE" />
          <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} stroke="#10b981" />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
            formatter={(value, name) => [name === '대출잔액' ? `${value}만원` : `${value}점`, name]}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="대출잔액"
            stroke="#3182CE"
            strokeWidth={2}
            dot={{ r: 3 }}
            name="대출 잔액 (만원)"
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="신용점수"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ r: 3 }}
            name="신용 점수"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
