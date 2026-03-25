import React from 'react'
import { AlertTriangle, Info, CheckCircle, Clock } from 'lucide-react'

const severityConfig = {
  high: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-400',
    dot: 'status-danger',
    icon: AlertTriangle,
    label: 'HIGH',
  },
  medium: {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    dot: 'status-warning',
    icon: AlertTriangle,
    label: 'MED',
  },
  low: {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    dot: '',
    icon: Info,
    label: 'LOW',
  },
  resolved: {
    bg: 'bg-slate-500/10',
    border: 'border-slate-500/20',
    text: 'text-slate-400',
    dot: '',
    icon: CheckCircle,
    label: 'OK',
  },
}

function AlertCard({ alert }) {
  const { type, message, location, time, severity, camera } = alert
  const config = severityConfig[severity] || severityConfig.low

  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${config.bg} ${config.border} transition-all duration-200 hover:brightness-110`}>
      <div className={`w-7 h-7 rounded flex items-center justify-center flex-shrink-0 mt-0.5 ${config.bg}`}>
        <config.icon className={`w-3.5 h-3.5 ${config.text}`} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className={`text-[10px] font-bold text-mono ${config.text} tracking-wider`}>
            [{config.label}]
          </span>
          <span className="text-xs text-slate-900 font-medium truncate">{type}</span>
        </div>
        <p className="text-xs text-slate-600 truncate">{message}</p>
        <div className="flex items-center gap-3 mt-1">
          {location && (
            <span className="text-[10px] text-slate-500 text-mono">{location}</span>
          )}
          {camera && (
            <span className="text-[10px] text-sky-700 text-mono">{camera}</span>
          )}
        </div>
      </div>

      <div className="flex flex-col items-end gap-1 flex-shrink-0">
        <div className="flex items-center gap-1 text-[10px] text-slate-500 text-mono">
          <Clock className="w-2.5 h-2.5" />
          {time}
        </div>
        {(severity === 'high' || severity === 'medium') && (
          <span className={`status-dot ${config.dot}`} />
        )}
      </div>
    </div>
  )
}

export default AlertCard
