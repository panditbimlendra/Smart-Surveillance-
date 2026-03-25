import React from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Hero from '../components/Hero'
import FeatureCard from '../components/FeatureCard'
import Logo from '../components/Logo'
import HowItWorks from '../components/HowItWorks'
import WhereItIsUsed from '../components/WhereItIsUsed'
import {
  Eye, Mic, MapPin, Video, Bell, FileText,
  ArrowRight, Github, Twitter, Linkedin
} from 'lucide-react'

const features = [
  {
    icon: Eye,
    title: 'Real-Time Object Detection',
    description: 'YOLOv8-powered detection identifies people, vehicles, and objects with 97%+ accuracy at 30fps.',
    accentColor: 'cyan',
  },
  {
    icon: Mic,
    title: 'Audio Threat Detection',
    description: 'ML-based audio analysis detects gunshots, glass breaks, and anomalous sounds in milliseconds.',
    accentColor: 'blue',
  },
  {
    icon: MapPin,
    title: 'GPS Alert Mapping',
    description: 'Geo-tag every event and visualize threat distribution across your facility in real time.',
    accentColor: 'amber',
  },
  {
    icon: Video,
    title: 'Live CCTV Monitoring',
    description: 'Unified multi-feed dashboard supports up to 64 simultaneous HD camera streams.',
    accentColor: 'cyan',
  },
  {
    icon: Bell,
    title: 'Automated Alert System',
    description: 'Smart alert routing delivers notifications via SMS, email, and push—with severity triage.',
    accentColor: 'purple',
  },
  {
    icon: FileText,
    title: 'Event Logging System',
    description: 'Tamper-proof, timestamped logs of every detection event for forensic review and compliance.',
    accentColor: 'blue',
  },
]

function Landing() {
  const navigate = useNavigate()

  return (
    <div id="top" className="min-h-screen bg-[#030712] text-white">
      <Navbar />
      <Hero />

      {/* Features Section */}
      <section id="features" className="py-24 px-6 relative">
        <div className="absolute inset-0 grid-bg opacity-30" />
        <div className="max-w-6xl mx-auto relative">
          <div className="text-center mb-16">
            <p className="text-xs text-mono text-cyan-400 uppercase tracking-widest mb-3">What it does</p>
            <h2 className="text-display text-3xl font-bold text-white mb-4">
              Real-Time AI Surveillance System
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto text-sm leading-relaxed">
              Built to detect and respond to unusual activity instantly using AI-powered monitoring.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((feature, i) => (
              <FeatureCard key={feature.title} {...feature} index={i} />
            ))}
          </div>
        </div>
      </section>

      <HowItWorks />
      <WhereItIsUsed />

      {/* CTA Section */}
      <section className="py-24 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-950/10 to-transparent" />
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-cyan-500/3 rounded-full blur-xl pointer-events-none" />

        <div className="max-w-3xl mx-auto text-center relative">
          <div className="glass-card p-12 border-cyan-400/20">
            <div className="flex justify-center mb-6">
              <Logo size="lg" />
            </div>
            <h2 className="text-display text-3xl font-bold text-white mb-4">
              Ready to Make Your<br />Environment Safer?
            </h2>
            <p className="text-slate-400 mb-8 text-sm leading-relaxed">
              Join security teams worldwide using SafeZone AI to protect what matters most.
            </p>
            <button
              onClick={() => navigate('/login')}
              className="btn-primary text-sm inline-flex items-center gap-2"
            >
              Start Monitoring Now
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div className="md:col-span-2">
              <div className="flex items-center gap-2 mb-3">
                <Logo size="sm" />
                <span className="text-display text-sm font-bold text-white tracking-wider">
                  SAFE<span className="text-cyan-400">ZONE</span>
                </span>
              </div>
              <p className="text-slate-500 text-xs leading-relaxed max-w-xs">
                Multi-modal AI surveillance system for real-time threat detection and security monitoring.
              </p>
            </div>

            {[
              {
                title: 'Features',
                links: ['Live Monitoring', 'Smart Alerts', 'Event Logs', 'Map View'],
              },
              {
                title: 'Contact',
                links: [
                  'Email: contact.safezone@gmail.com',
                  'Phone: +977 98XXXXXXXX'
                ],
              },
            ].map(({ title, links }) => (
              <div key={title}>
                <h4 className="text-xs font-semibold text-white uppercase tracking-widest mb-3">{title}</h4>
                <ul className="space-y-2">
                  {links.map((link) => (
                    <li key={link}>
                      <a href="#" className="text-xs text-slate-500 hover:text-cyan-400 transition-colors">
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="border-t border-white/5 pt-6 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-xs text-slate-600">
              © 2026 SafeZone. All rights reserved.
            </p>
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-3">
                {[Github, Twitter, Linkedin].map((Icon, i) => (
                  <a
                    key={i}
                    href="#"
                    className="text-slate-600 hover:text-cyan-400 transition-colors"
                  >
                    <Icon className="w-4 h-4" />
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default Landing