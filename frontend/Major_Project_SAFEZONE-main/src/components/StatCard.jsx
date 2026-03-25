import React from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

function StatCard({ title, value, subtitle, icon: Icon, trend, trendValue, accentColor = 'cyan' }) {
  const colors = {
    cyan: { text: 'text-cyan-400', bg: 'bg-cyan-400/10', border: 'border-cyan-400/20' },
    red: { text: 'text-red-400', bg: 'bg-red-400/10', border: 'border-red-400/20' },
    amber: { text: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20' },
    green: { text: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/20' },
  }

  const color = colors[accentColor] || colors.cyan

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-slate-500'

  return (
    <div className={`glass-card p-5 border ${color.border} hover:border-opacity-40 transition-all duration-300 group`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-slate-600 uppercase tracking-widest font-medium mb-1">{title}</p>
          <p className={`text-3xl font-bold text-display ${color.text}`}>{value}</p>
          {subtitle && (
            <p className="text-sm text-slate-700 mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`w-10 h-10 rounded-lg ${color.bg} flex items-center justify-center flex-shrink-0 ml-3 group-hover:scale-110 transition-transform`}>
          <Icon className={`w-5 h-5 ${color.text}`} />
        </div>
      </div>

      {trendValue && (
        <div className={`flex items-center gap-1 mt-3 ${trendColor} text-sm text-mono`}>
          <TrendIcon className="w-3.5 h-3.5" />
          <span>{trendValue}</span>
        </div>
      )}
    </div>
  )
}

export default StatCard
