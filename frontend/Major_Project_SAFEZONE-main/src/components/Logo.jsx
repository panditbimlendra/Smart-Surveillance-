import React from 'react'
import { Shield } from 'lucide-react'

function Logo({ size = 'sm', className = '' }) {
  const sizeClasses = {
    sm: 'w-7 h-7',
    lg: 'w-12 h-12'
  }

  return (
    <div className={`relative ${className}`}>
      <Shield className={`${sizeClasses[size]} text-sky-700`} />
    </div>
  )
}

export default Logo
