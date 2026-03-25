import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Bell, FileText, Map, Settings, LogOut, ChevronRight } from 'lucide-react'
import { useAuth } from '../App'
import { useNavigate } from 'react-router-dom'
import Logo from './Logo'

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
  { icon: Bell, label: 'Alerts', path: '/alerts' },
  { icon: FileText, label: 'Event Logs', path: '/logs' },
  { icon: Map, label: 'Map View', path: '/map' },
]

function Sidebar({ collapsed, onToggle }) {
  const location = useLocation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <aside className={`fixed top-0 left-0 h-full z-40 flex flex-col transition-all duration-300 ${
      collapsed ? 'w-16' : 'w-60'
    } bg-white/92 backdrop-blur-xl border-r border-slate-200 shadow-xl`}>

      {/* Logo */}
      <div className={`flex items-center gap-3 px-4 py-5 border-b border-slate-200 ${collapsed ? 'justify-center' : ''}`}>
        <Logo />
        {!collapsed && (
          <span className="text-display text-sm font-bold text-slate-900 tracking-wider whitespace-nowrap">
            SAFE<span className="text-sky-600">ZONE</span>
          </span>
        )}
      </div>

     

      {/* Nav Items */}
      <nav className="flex-1 px-2 mt-4 space-y-1">
        {navItems.map(({ icon: Icon, label, path }) => {
          const active = location.pathname === path
          return (
            <Link
              key={path}
              to={path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group relative ${
                active
                  ? 'bg-sky-100 text-sky-700 border border-sky-200'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              } ${collapsed ? 'justify-center' : ''}`}
              title={collapsed ? label : ''}
            >
              <Icon className={`w-4 h-4 flex-shrink-0 ${active ? 'text-sky-700' : ''}`} />
              {!collapsed && (
                <span className="text-sm font-medium tracking-wide">{label}</span>
              )}
              {active && !collapsed && (
                <ChevronRight className="w-3 h-3 ml-auto text-sky-600/70" />
              )}
              {active && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-sky-600 rounded-r" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Bottom Section */}
      <div className="px-2 pb-4 space-y-1 border-t border-slate-200 pt-4">
        

        {!collapsed && user && (
          <div className="px-3 py-2 mt-2">
            <p className="text-xs text-slate-400 font-medium truncate">{user.name}</p>
            <p className="text-xs text-slate-500 truncate">{user.email}</p>
          </div>
        )}

        <button
          onClick={handleLogout}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-red-500/70 hover:text-red-400 hover:bg-red-500/5 transition-all ${collapsed ? 'justify-center' : ''}`}
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {!collapsed && <span className="text-sm font-medium">Logout</span>}
        </button>
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-16 w-6 h-6 rounded-full bg-white border border-slate-300 flex items-center justify-center text-sky-600 hover:border-sky-400 transition-colors shadow"
      >
        <ChevronRight className={`w-3 h-3 transition-transform duration-300 ${collapsed ? '' : 'rotate-180'}`} />
      </button>
    </aside>
  )
}

export default Sidebar
