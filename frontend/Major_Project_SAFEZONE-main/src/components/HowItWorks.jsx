import React from 'react'
import { Camera, Brain, Bell, MapPin } from 'lucide-react'

const steps = [
  {
    icon: Camera,
    title: 'Capture Data',
    description: 'CCTV cameras & microphones collect real-time input',
    step: '01',
  },
  {
    icon: Brain,
    title: 'AI Analysis',
    description: 'Detects anomalies like gunshots, fire, suspicious activity',
    step: '02',
  },
  {
    icon: Bell,
    title: 'Instant Alerts',
    description: 'Sends alerts immediately to users and the system',
    step: '03',
  },
  {
    icon: MapPin,
    title: 'GPS Navigation',
    description: 'Shows exact location for quick response',
    step: '04',
  },
]

function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 px-6 relative">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <p className="text-xs font-mono text-cyan-400 uppercase tracking-widest mb-3">WORKFLOW</p>
          <h2 className="text-3xl font-bold text-white">
            How the System <span className="text-cyan-400">Works</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {steps.map(({ icon: Icon, title, description, step }) => (
            <div
              key={step}
              className="relative flex flex-col items-center text-center p-6 rounded-xl border border-white/5 bg-white/[0.02] hover:border-cyan-400/20 hover:bg-white/[0.04] hover:scale-[1.02] transition-all duration-300 group"
            >
              <span className="absolute top-3 right-4 text-xs font-mono text-white/10 group-hover:text-cyan-400/20 transition-colors">
                {step}
              </span>
              <div className="w-10 h-10 rounded-lg bg-cyan-400/5 border border-cyan-400/15 flex items-center justify-center mb-4 group-hover:bg-cyan-400/10 transition-colors">
                <Icon className="w-5 h-5 text-cyan-400" />
              </div>
              <h3 className="text-sm font-semibold text-white mb-2">{title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default HowItWorks