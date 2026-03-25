import React, { useState } from 'react'
import Sidebar from './Sidebar'
import { Bell } from 'lucide-react'

function DashboardLayout({ children, notifications = [], onBellClick, showNotifPanel, notifPanelRef }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const unreadCount = notifications.filter(n => !n.read).length

  const notifColors = {
    critical: 'text-red-400 bg-red-400/10 border-red-400/20',
    warning:  'text-amber-400 bg-amber-400/10 border-amber-400/20',
    info:     'text-blue-400 bg-blue-400/10 border-blue-400/20',
  }

  return (
    <div className="min-h-screen bg-transparent flex text-slate-900">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      <div
        className="flex-1 flex flex-col transition-all duration-300"
        style={{ marginLeft: sidebarCollapsed ? '4rem' : '15rem' }}
      >
        {/* Top Bar */}
        <header className="sticky top-0 z-30 bg-white/72 backdrop-blur-xl border-b border-slate-300/60 px-6 py-3 flex items-center justify-between shadow-sm">
          <span className="text-display text-base font-bold text-slate-900 tracking-widest uppercase">
            Control Centre
          </span>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-1.5 text-sm text-emerald-700 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              System Active
            </div>

            {/* Bell */}
            <div className="relative" ref={notifPanelRef}>
              <button
                onClick={onBellClick}
                className="relative p-2 text-slate-500 hover:text-slate-900 transition-colors"
              >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-5 h-5 bg-red-500 rounded-full text-xs text-white flex items-center justify-center font-mono">
                    {unreadCount}
                  </span>
                )}
              </button>

              {showNotifPanel && (
                <div className="absolute right-0 top-10 w-72 bg-white border border-slate-200 rounded-xl shadow-2xl z-50 overflow-hidden">
                  <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-900 uppercase tracking-widest">Notifications</span>
                    <span className="text-xs font-mono text-slate-500">{unreadCount} unread</span>
                  </div>
                  <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                    {notifications.length === 0 ? (
                      <p className="text-sm text-slate-500 text-center py-6">No notifications</p>
                    ) : (
                      notifications.map(n => (
                        <div key={n.id} className={`px-4 py-3 flex items-start gap-3 ${!n.read ? 'bg-cyan-50/60' : 'bg-white'}`}>
                          <span className={`mt-0.5 text-xs font-mono px-1.5 py-0.5 rounded border ${notifColors[n.severity] || notifColors.info}`}>
                            {n.severity?.toUpperCase()}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-slate-800 leading-snug">{n.message}</p>
                            <p className="text-xs text-slate-500 font-mono mt-0.5">{n.time}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>


          </div>
        </header>

        <main className="flex-1 px-6 py-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}

export default DashboardLayout
