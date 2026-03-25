import React, { useEffect, useRef } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Shield, Activity, Eye, Zap, ArrowRight, Play } from 'lucide-react'

function MockDashboardCard() {
  return (
    <div className="relative animate-float">
      {/* Main Card */}
      <div className="glass-card p-5 w-full max-w-sm mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="status-dot status-online" />
            <span className="text-xs text-mono text-cyan-400">LIVE FEED </span>
          </div>
          <span className="text-xs text-mono text-slate-500">23:41:07</span>
        </div>

        {/* Fake Camera View */}
        <div className="relative rounded-lg overflow-hidden bg-[#050a14] aspect-video mb-4 scanline">
          {/* Grid lines */}
          <div className="absolute inset-0 grid-bg opacity-50" />

          {/* Detection Box */}
          <div className="absolute top-4 left-8 w-16 h-20 border border-red-400/80 rounded">
            <div className="absolute -top-4 left-0 bg-red-500/90 text-white text-[9px] px-1 py-0.5 text-mono rounded-sm">
              ACCIDENT 94%
            </div>
            <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-red-400" />
            <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-red-400" />
            <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-red-400" />
            <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-red-400" />
          </div>

          {/* Object Box 2 */}
          <div className="absolute top-8 right-10 w-12 h-8 border border-cyan-400/60 rounded">
            <div className="absolute -top-4 left-0 bg-cyan-500/90 text-white text-[9px] px-1 py-0.5 text-mono rounded-sm">
              VEH 87%
            </div>
          </div>

          {/* Crosshair */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-4 h-4 border border-cyan-400/20 rounded-full relative">
              <div className="absolute inset-0 border-t border-cyan-400/40" />
              <div className="absolute inset-0 border-l border-cyan-400/40" />
            </div>
          </div>

          {/* Bottom info bar */}
          <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-2 py-1 flex justify-between items-center">
            <span className="text-[9px] text-mono text-cyan-400">REC ●</span>
            <span className="text-[9px] text-mono text-slate-400">1920×1080 | 30fps</span>
            
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Alerts', value: '3', color: 'text-red-400' },
            { label: 'Online', value: '24', color: 'text-cyan-400' },
            { label: 'Events', value: '147', color: 'text-amber-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-[#0d1526] rounded p-2 text-center">
              <p className={`text-sm font-bold text-display ${color}`}>{value}</p>
              <p className="text-[10px] text-slate-500">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Floating Mini Cards */}
      <div className="absolute -top-3 -right-3 glass-card p-2 text-[10px] text-mono text-red-400 border-red-400/30 flex items-center gap-1.5 animate-pulse-slow">
        <span className="status-dot status-danger" />
        THREAT DETECTED
      </div>
      <div className="absolute -bottom-3 -left-3 glass-card p-2 text-[10px] text-mono text-cyan-400 flex items-center gap-1.5">
        <Activity className="w-3 h-3" />
        AI PROCESSING
      </div>
    </div>
  )
}

function Hero() {
  const navigate = useNavigate()
  const location = useLocation()

  const handleWatchDemo = () => {
    if (location.pathname === '/') {
      document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })
    } else {
      window.location.href = '/#demo'
    }
  }

  return (
    <section className="relative min-h-screen flex items-center pt-20 overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 grid-bg opacity-20 pointer-events-none" />
      <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-cyan-500/3 rounded-full blur-2xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-48 h-48 bg-blue-500/3 rounded-full blur-2xl pointer-events-none" />

      {/* Animated corner decorations */}
      {/* Removed boot status lines as requested */}

      <div className="max-w-7xl mx-auto px-6 py-20 grid lg:grid-cols-2 gap-16 items-center relative z-10">
        {/* Left Text */}
        <div className="space-y-8">
          <h1 className="text-display text-4xl lg:text-5xl font-bold leading-tight text-white">
            AI-POWERED{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-blue-300">
              REAL-TIME SURVEILLANCE
            </span>
          </h1>

          <p className="text-slate-400 text-base leading-relaxed max-w-lg">
            Detect threats, monitor live feeds, and receive instant alerts across your entire security perimeter. 
            SafeZone AI combines computer vision, audio analysis, and GPS tracking in one unified platform.
          </p>

          <div className="flex flex-wrap gap-4">
            <Link to="/signup" className="btn-primary inline-flex items-center gap-2">
              Get Started
            </Link>

            
          </div>

          {/* Trust badges */}
          <div className="flex items-center gap-6 pt-4 border-t border-white/5">
            {[
              { icon: Eye, text: '24/7 Monitoring' },
              { icon: Zap, text: 'Real-time detection' },
              { icon: Shield, text: 'Secure by design' },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-2 text-slate-500 text-xs">
                <Icon className="w-3.5 h-3.5 text-cyan-400/60" />
                {text}
              </div>
            ))}
          </div>
        </div>

        {/* Right: Mock Dashboard */}
        <div className="flex justify-center lg:justify-end">
          <div className="relative w-full max-w-sm">
            <MockDashboardCard />
            {/* Decorative ring */}
            <div className="absolute -inset-6 border border-cyan-400/5 rounded-2xl" />
            <div className="absolute -inset-12 border border-cyan-400/3 rounded-3xl" />
          </div>
        </div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#030712] to-transparent pointer-events-none" />
    </section>
  )
}

export default Hero
