import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Shield, Menu, X } from 'lucide-react'

function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
      scrolled
        ? 'bg-[#030712]/90 backdrop-blur-xl border-b border-cyan-400/10'
        : 'bg-transparent'
    }`}>
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="relative">
            <Shield className="w-7 h-7 text-cyan-300" />
            <div className="absolute inset-0 bg-cyan-400/40 rounded-full blur-md" />
          </div>
          <span className="text-display text-base font-bold text-white tracking-wider">
            SAFE<span className="text-cyan-400">ZONE</span>
            <span className="text-cyan-400/60 text-xs ml-1"></span>
          </span>
        </Link>

        {/* Desktop Links */}
        <div className="hidden md:flex items-center gap-8">
          <a
            href="#top"
            className="text-sm font-medium text-slate-400 hover:text-cyan-400 transition-colors duration-200 tracking-wide"
          >
            Home
          </a>
          {['Features', 'How it Works'].map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
              className="text-sm font-medium text-slate-400 hover:text-cyan-400 transition-colors duration-200 tracking-wide"
            >
              {item}
            </a>
          ))}
        </div>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-3">
          <Link to="/login" className="text-sm text-slate-400 hover:text-white transition-colors px-4 py-2">
            Login
          </Link>
          <button
            onClick={() => navigate('/signup')}
            className="btn-primary"
          >
            Get Started
          </button>
        </div>

        {/* Mobile Toggle */}
        <button
          className="md:hidden text-cyan-400 p-2"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden bg-[#0a0f1e]/95 backdrop-blur-xl border-b border-cyan-400/10 px-6 py-4 flex flex-col gap-4">
          <a
            href="#top"
            className="text-sm text-slate-400 hover:text-cyan-400 transition-colors py-2"
            onClick={() => setMobileOpen(false)}
          >
            Home
          </a>
          {['Features', 'Demo', 'About'].map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
              className="text-sm text-slate-400 hover:text-cyan-400 transition-colors py-2"
              onClick={() => setMobileOpen(false)}
            >
              {item}
            </a>
          ))}
          <Link to="/login" className="text-sm text-slate-400 hover:text-white transition-colors py-2">
            Login
          </Link>
          <button onClick={() => navigate('/signup')} className="btn-primary text-center">
            Get Started
          </button>
        </div>
      )}
    </nav>
  )
}

export default Navbar
