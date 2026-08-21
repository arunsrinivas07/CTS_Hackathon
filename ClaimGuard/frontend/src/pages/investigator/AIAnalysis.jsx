import { useState } from 'react';
import { Brain, TrendingUp, AlertTriangle, BarChart3, RefreshCw } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import RiskMeter from '../../components/ui/RiskMeter';
import ClaimsBarChart from '../../components/charts/ClaimsBarChart';
import RiskBarChart from '../../components/charts/RiskBarChart';
import ClaimsPieChart from '../../components/charts/ClaimsPieChart';
import { investigations, providers } from '../../data/mockData';

const insights = [
  {
    id: 1,
    type: 'critical',
    title: 'Unbundling Pattern Detected',
    description: 'Riverside Medical Center has submitted 7 claims in the last 60 days where cardiac procedure codes were billed separately instead of using standard bundle codes. Estimated overbilling: $180,000.',
    provider: 'Riverside Medical Center',
    confidence: 94,
  },
  {
    id: 2,
    type: 'warning',
    title: 'Duplicate Billing Risk',
    description: 'Patient James Thornton (PAT-4421) has two claims within 30 days for similar appendectomy-related procedures. High probability of duplicate submission.',
    provider: 'Riverside Medical Center',
    confidence: 82,
  },
  {
    id: 3,
    type: 'warning',
    title: 'High-Cost Outlier Cluster',
    description: 'Northside Neurological\'s inpatient claims average $58,000 vs. the peer average of $38,000 for equivalent procedures. Recommend peer comparison audit.',
    provider: 'Northside Neurological',
    confidence: 76,
  },
  {
    id: 4,
    type: 'info',
    title: 'Documentation Completeness Improving',
    description: 'Valley Orthopedics has achieved 100% documentation compliance over the last 3 months. No active flags.',
    provider: 'Valley Orthopedics',
    confidence: 99,
  },
];

const insightColors = {
  critical: 'border-red-200 bg-red-50',
  warning: 'border-amber-200 bg-amber-50',
  info: 'border-rose-200 bg-rose-50',
};

const insightIconColors = {
  critical: 'text-red-500',
  warning: 'text-amber-500',
  info: 'text-rose-500',
};

export default function AIAnalysis() {
  const [refreshing, setRefreshing] = useState(false);
  const [refreshed, setRefreshed] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await new Promise(r => setTimeout(r, 1200));
    setRefreshing(false);
    setRefreshed(true);
    setTimeout(() => setRefreshed(false), 3000);
  };

  return (
    <div>
      <PageHeader
        title="AI Business Analysis"
        subtitle="AI-powered insights on fraud patterns, risk trends, and claim anomalies."
        actions={
          <button className="btn-secondary" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            {refreshed ? 'Updated' : 'Refresh Analysis'}
          </button>
        }
      />

      {/* Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Fraud Patterns Found', value: '3', color: 'text-red-600', bg: 'bg-red-50' },
          { label: 'Claims Analyzed', value: '336', color: 'text-rose-700', bg: 'bg-rose-50' },
          { label: 'Est. Savings at Risk', value: '$384k', color: 'text-emerald-700', bg: 'bg-emerald-50' },
          { label: 'Avg. Confidence', value: '88%', color: 'text-violet-700', bg: 'bg-violet-50' },
        ].map(({ label, value, color, bg }) => (
          <div key={label} className={`card p-4 ${bg}`}>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
            <p className="text-xs text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* AI Insights */}
      <div className="card p-5 mb-5">
        <div className="flex items-center gap-2 mb-4">
          <Brain size={18} className="text-violet-600" />
          <h3 className="section-title">AI-Generated Insights</h3>
        </div>
        <div className="space-y-3">
          {insights.map(ins => (
            <div key={ins.id} className={`rounded-lg border p-4 ${insightColors[ins.type]}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <AlertTriangle size={16} className={`mt-0.5 flex-shrink-0 ${insightIconColors[ins.type]}`} />
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800">{ins.title}</p>
                    <p className="text-xs text-slate-600 mt-1 leading-relaxed">{ins.description}</p>
                    <p className="text-xs text-slate-400 mt-1.5">Provider: {ins.provider}</p>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                  <Badge status={ins.type} />
                  <span className="text-xs text-slate-500">Confidence: <strong>{ins.confidence}%</strong></span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="card p-5 lg:col-span-2">
          <h3 className="section-title mb-4">Claims Trend Analysis</h3>
          <ClaimsBarChart />
        </div>
        <div className="card p-5">
          <h3 className="section-title mb-4">Claims by Type</h3>
          <ClaimsPieChart />
        </div>
        <div className="card p-5 lg:col-span-3">
          <h3 className="section-title mb-4">Risk Score Distribution</h3>
          <RiskBarChart />
        </div>
      </div>
    </div>
  );
}
