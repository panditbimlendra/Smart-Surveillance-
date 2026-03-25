import React from 'react'
import { GraduationCap, Briefcase, Home, Users, Shield, Factory } from 'lucide-react'

const useCases = [
  { icon: GraduationCap, label: 'Schools & Colleges' },
  { icon: Briefcase,     label: 'Offices & Workspaces' },
  { icon: Home,          label: 'Smart Homes' },
  { icon: Users,         label: 'Public Spaces' },
  { icon: Shield,        label: 'Security Agencies' },
  { icon: Factory,       label: 'Industrial Areas' },
]

function WhereItIsUsed() {
  return (
    <section className="py-20 px-6 relative">
      <div className="absolute inset-0 grid-bg opacity-20" />
      <div className="max-w-6xl mx-auto relative">
        <div className="text-center mb-14">
          <p className="text-xs font-mono text-cyan-400 uppercase tracking-widest mb-3">APPLICATIONS</p>
          <h2 className="text-3xl font-bold text-white">
            Powered for Real-World  <span className="text-cyan-400"> Environments</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {useCases.map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-4 p-5 rounded-xl border border-white/5 bg-white/[0.02] hover:border-cyan-400/20 hover:bg-white/[0.04] hover:scale-[1.01] transition-all duration-300 group"
            >
              <div className="w-9 h-9 rounded-lg bg-cyan-400/5 border border-cyan-400/10 flex items-center justify-center shrink-0 group-hover:bg-cyan-400/10 transition-colors">
                <Icon className="w-4 h-4 text-cyan-400" />
              </div>
              <span className="text-sm font-medium text-slate-300 group-hover:text-white transition-colors">
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default WhereItIsUsed