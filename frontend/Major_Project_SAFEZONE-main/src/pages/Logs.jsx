import React, { useEffect, useMemo, useState } from 'react'
import { Download, FileText, Search } from 'lucide-react'
import DashboardLayout from '../components/DashboardLayout'
import { getRecentLogs } from '../lib/api'

const typeColors = {
  THREAT: 'text-red-400 bg-red-400/10',
  AUDIO: 'text-purple-400 bg-purple-400/10',
  BEHAVIOR: 'text-amber-400 bg-amber-400/10',
  OBJECT: 'text-cyan-400 bg-cyan-400/10',
  MOTION: 'text-blue-400 bg-blue-400/10',
  SYSTEM: 'text-slate-400 bg-slate-400/10',
  ACCESS: 'text-emerald-400 bg-emerald-400/10',
}

const statusColors = {
  ACTIVE: 'text-red-400 bg-red-400/10 border-red-400/20',
  REVIEW: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  LOGGED: 'text-slate-400 bg-slate-400/10 border-slate-400/10',
  RESOLVED: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
}

function Logs() {
  const [logs, setLogs] = useState([])
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('ALL')

  useEffect(() => {
    let active = true

    async function loadLogs() {
      try {
        const data = await getRecentLogs(100)
        if (active) setLogs(data)
      } catch (error) {
        console.error('Failed to load logs', error)
      }
    }

    loadLogs()
    return () => {
      active = false
    }
  }, [])

  const allTypes = useMemo(() => ['ALL', ...Array.from(new Set(logs.map((log) => log.type)))], [logs])

  const filtered = useMemo(() => {
    return logs.filter((log) => {
      const matchType = typeFilter === 'ALL' || log.type === typeFilter
      const query = search.toLowerCase()
      const matchSearch =
        !query ||
        log.event.toLowerCase().includes(query) ||
        log.zone.toLowerCase().includes(query) ||
        log.camera.toLowerCase().includes(query)
      return matchType && matchSearch
    })
  }, [logs, search, typeFilter])

  return (
    <DashboardLayout title="Event Logs" subtitle="Audit trail from SafeZone backend events">
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search events, zones, cameras..."
            className="w-full bg-white/5 border border-white/8 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-cyan-400/30 transition-all"
          />
        </div>

        <div className="flex gap-2 flex-wrap">
          {allTypes.map((type) => (
            <button
              key={type}
              onClick={() => setTypeFilter(type)}
              className={`px-3 py-1.5 rounded-lg text-[10px] text-mono border transition-all ${
                typeFilter === type
                  ? typeColors[type] || 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20'
                  : 'border-white/10 text-slate-500 hover:border-white/20'
              }`}
            >
              {type}
            </button>
          ))}
        </div>

        <button className="flex items-center gap-1.5 px-3 py-2 text-xs text-mono text-slate-500 border border-white/8 rounded-lg ml-auto whitespace-nowrap cursor-default">
          <Download className="w-3.5 h-3.5" />
          Backend audit feed
        </button>
      </div>

      <div className="flex items-center gap-4 mb-4 text-xs text-mono text-slate-500">
        <span className="text-cyan-400">{filtered.length}</span> events shown
        <span>·</span>
        <span>Live from audit.jsonl</span>
      </div>

      <div className="glass-card overflow-hidden">
        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">No logs match your filter.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/5 bg-white/2">
                  {['#', 'Timestamp', 'Event', 'Zone / Location', 'Camera', 'Type', 'Status'].map((heading) => (
                    <th
                      key={heading}
                      className="text-left text-[10px] text-slate-500 uppercase tracking-widest font-medium px-4 py-3 whitespace-nowrap"
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((log, index) => (
                  <tr key={log.id} className="border-b border-white/3 hover:bg-white/2 transition-colors">
                    <td className="px-4 py-3 text-[10px] text-mono text-slate-600">{String(index + 1).padStart(3, '0')}</td>
                    <td className="px-4 py-3 text-xs text-mono text-slate-400 whitespace-nowrap">{log.time}</td>
                    <td className="px-4 py-3 text-xs text-white font-medium whitespace-nowrap">{log.event}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{log.zone}</td>
                    <td className="px-4 py-3 text-xs text-mono text-cyan-400/70">{log.camera}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] text-mono font-medium px-1.5 py-0.5 rounded ${typeColors[log.type] || 'text-slate-400'}`}>
                        {log.type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] text-mono border px-2 py-0.5 rounded ${statusColors[log.status] || 'text-slate-400'}`}>
                        {log.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}

export default Logs
