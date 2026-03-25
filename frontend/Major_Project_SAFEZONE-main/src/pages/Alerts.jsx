import React, { useEffect, useMemo, useState } from 'react'
import { Bell, RefreshCw, Search } from 'lucide-react'
import AlertCard from '../components/AlertCard'
import DashboardLayout from '../components/DashboardLayout'
import { getRecentAlerts } from '../lib/api'

const severityFilters = ['all', 'high', 'medium', 'low']

function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    async function loadAlerts() {
      try {
        const data = await getRecentAlerts(50)
        if (active) setAlerts(data)
      } catch (error) {
        console.error('Failed to load alerts', error)
      } finally {
        if (active) setLoading(false)
      }
    }

    loadAlerts()
    return () => {
      active = false
    }
  }, [])

  const filtered = useMemo(() => {
    return alerts.filter((alert) => {
      const matchesSeverity = filter === 'all' || alert.severity === filter
      const query = search.toLowerCase()
      const matchesSearch =
        !query ||
        alert.type.toLowerCase().includes(query) ||
        alert.message.toLowerCase().includes(query) ||
        alert.location.toLowerCase().includes(query)
      return matchesSeverity && matchesSearch
    })
  }, [alerts, filter, search])

  const counts = {
    all: alerts.length,
    high: alerts.filter((alert) => alert.severity === 'high').length,
    medium: alerts.filter((alert) => alert.severity === 'medium').length,
    low: alerts.filter((alert) => alert.severity === 'low').length,
  }

  const filterColors = {
    all: 'border-cyan-400/30 text-cyan-400 bg-cyan-400/10',
    high: 'border-red-400/30 text-red-400 bg-red-400/10',
    medium: 'border-amber-400/30 text-amber-400 bg-amber-400/10',
    low: 'border-emerald-400/30 text-emerald-400 bg-emerald-400/10',
  }

  return (
    <DashboardLayout title="Alert Center" subtitle="Live alerts from the SafeZone backend">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {['high', 'medium', 'low'].map((sev) => {
          const colors = {
            high: { text: 'text-red-400', border: 'border-red-400/20' },
            medium: { text: 'text-amber-400', border: 'border-amber-400/20' },
            low: { text: 'text-emerald-400', border: 'border-emerald-400/20' },
          }[sev]

          return (
            <div key={sev} className={`glass-card p-4 border ${colors.border}`}>
              <p className={`text-2xl font-bold text-display ${colors.text}`}>{counts[sev]}</p>
              <p className="text-xs text-slate-500 uppercase tracking-widest mt-1">{sev}</p>
            </div>
          )
        })}
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search alerts..."
            className="w-full bg-white/5 border border-white/8 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-cyan-400/30 transition-all"
          />
        </div>

        <div className="flex gap-2 flex-wrap">
          {severityFilters.map((sev) => (
            <button
              key={sev}
              onClick={() => setFilter(sev)}
              className={`px-3 py-1.5 rounded-lg text-[10px] text-mono uppercase tracking-wider border transition-all ${
                filter === sev
                  ? filterColors[sev]
                  : 'border-white/10 text-slate-500 hover:border-white/20 hover:text-slate-400'
              }`}
            >
              {sev} {sev !== 'all' && `(${counts[sev]})`}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5 px-3 py-2 text-xs text-mono text-slate-500 border border-white/8 rounded-lg ml-auto">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Live feed
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Bell className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500 text-sm">No alerts match your filter.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </DashboardLayout>
  )
}

export default Alerts
