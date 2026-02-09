import CustomerHeader from './components/CustomerHeader'
import LoanCreditChart from './components/LoanCreditChart'
import ConsultationTimeline from './components/ConsultationTimeline'
import MiniERDWidget from './components/MiniERDWidget'
import {
  customer,
  scores,
  loanBalanceHistory,
  creditScoreHistory,
  consultations,
} from './data/mockCustomer'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      <CustomerHeader customer={customer} scores={scores} />

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <LoanCreditChart
              loanData={loanBalanceHistory}
              creditData={creditScoreHistory}
            />
          </div>
          <div>
            <ConsultationTimeline items={consultations} />
          </div>
        </div>

        <div className="mt-6">
          <MiniERDWidget />
        </div>
      </main>
    </div>
  )
}
