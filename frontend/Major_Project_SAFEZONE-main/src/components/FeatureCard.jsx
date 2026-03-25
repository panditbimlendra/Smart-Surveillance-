import React from 'react'

function FeatureCard({ icon: Icon, title, description, accentColor = 'cyan', index = 0 }) {
  const colors = {
    cyan: {
      icon: 'text-cyan-400',
      bg: 'bg-cyan-400/10',
      border: 'hover:border-cyan-400/40',
      glow: 'hover:shadow-cyan-400/5',
    },
    blue: {
      icon: 'text-blue-400',
      bg: 'bg-blue-400/10',
      border: 'hover:border-blue-400/40',
      glow: 'hover:shadow-blue-400/5',
    },
    purple: {
      icon: 'text-purple-400',
      bg: 'bg-purple-400/10',
      border: 'hover:border-purple-400/40',
      glow: 'hover:shadow-purple-400/5',
    },
    amber: {
      icon: 'text-amber-400',
      bg: 'bg-amber-400/10',
      border: 'hover:border-amber-400/40',
      glow: 'hover:shadow-amber-400/5',
    },
  }

  const color = colors[accentColor] || colors.cyan

  return (
    <div
      className={`glass-card-hover p-6 group cursor-default hover:shadow-lg ${color.border} ${color.glow}`}
      style={{ animationDelay: `${index * 0.1}s` }}
    >
      <div className={`w-10 h-10 rounded-lg ${color.bg} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
        <Icon className={`w-5 h-5 ${color.icon}`} />
      </div>

      <h3 className="text-white font-semibold text-sm mb-2 tracking-wide">{title}</h3>
      <p className="text-slate-500 text-sm leading-relaxed">{description}</p>

      {/* Bottom accent line */}
      <div className={`mt-4 h-px w-0 ${color.bg} group-hover:w-full transition-all duration-500 rounded`} />
    </div>
  )
}

export default FeatureCard
