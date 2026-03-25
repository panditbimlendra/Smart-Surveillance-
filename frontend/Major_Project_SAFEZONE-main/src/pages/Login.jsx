import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Eye, EyeOff, Lock, Mail, ArrowRight, AlertCircle } from 'lucide-react'
import { useAuth } from '../App'
import Logo from '../components/Logo'

function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!email || !password) {
      setError('Please fill in all fields')
      return
    }

    setLoading(true)

    // Simulate async auth
    await new Promise((r) => setTimeout(r, 1200))

    // Fake auth — any credentials work, just demo
    if (password.length < 4) {
      setError('Invalid credentials. Try: demo@safezone.ai / admin1234')
      setLoading(false)
      return
    }

    login(email)
    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen bg-[#030712] flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 grid-bg opacity-40" />
      <div className="absolute top-1/4 left-1/4 w-80 h-80 bg-cyan-500/5 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-60 h-60 bg-blue-500/5 rounded-full blur-3xl" />

      

      <div className="w-full max-w-sm relative">
        {/* Card */}
        <div className="glass-card p-8 border border-cyan-400/15">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
             <Logo size="lg" />
            </div>

            <h1 className="text-display text-xl font-bold text-white tracking-wider">
              Welcome Back
            </h1>
            <p className="text-slate-500 text-xs mt-1">SafeZone Control Center</p>
          </div>

          
          {/* Form */}
          <form onSubmit={handleSubmit} autoComplete="off" className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-xs text-slate-400 uppercase tracking-widest mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="email"
                  value={email}
                  autoComplete="new-email"
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email..."
                  className="w-full bg-[#050a14] border border-white/10 rounded-lg pl-10 pr-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/20 transition-all"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs text-slate-400 uppercase tracking-widest mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-[#050a14] border border-white/10 rounded-lg pl-10 pr-10 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/20 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-3 flex items-center justify-center gap-2 relative overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-[#030712]/30 border-t-[#030712] rounded-full animate-spin" />
                  Authenticating...
                </>
              ) : (
                <>
                  Login
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
          <div className="mt-6 text-center text-xs text-slate-500">
  Don’t have an account?{" "}
  <Link
    to="/signup"
    className="text-cyan-400 font-medium hover:text-cyan-300 hover:underline transition-all"
  >
    Create now
  </Link>
</div>

          <div className="mt-6 text-center">
            <Link to="/" className="text-xs text-slate-500 hover:text-slate-400 transition-colors">
              ← Back to SafeZone AI
            </Link>
          </div>
        </div>

        {/* Bottom status */}
        <div className="flex items-center justify-center gap-2 mt-4 text-[10px] text-mono text-slate-600">
          <span className="status-dot status-online" />
          Auth server online  End to End encrypted
        </div>
      </div>
    </div>
  )
}

export default Login
