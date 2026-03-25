import React, { useState, useEffect } from 'react'
import { Maximize2, AlertTriangle, Wifi, WifiOff } from 'lucide-react'

function CameraFeed({ camera }) {
  const { id, label, status, alerts, fps } = camera
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const timeStr = time.toLocaleTimeString('en-US', { hour12: false })

  const statusColors = {
    online: 'border-cyan-400/20',
    alert: 'border-red-400/40',
    offline: 'border-slate-700/40',
  }

  const dotColors = {
    online: 'status-online',
    alert: 'status-danger',
    offline: 'bg-slate-600',
  }

  // Pseudo-random detection boxes per camera
  const detectionBoxes = {
    CAM_07: [
      { x: 20, y: 15, w: 18, h: 32, label: 'PERSON 94%', color: 'red' },
    ],
    CAM_01: [
      { x: 55, y: 20, w: 22, h: 35, label: 'PERSON 89%', color: 'amber' },
    ],
    CAM_02: [
      { x: 30, y: 40, w: 28, h: 15, label: 'OBJECT 76%', color: 'amber' },
    ],
    CAM_03: [
      { x: 10, y: 50, w: 30, h: 22, label: 'VEHICLE 91%', color: 'cyan' },
    ],
  }

  const boxes = detectionBoxes[id] || []

  return (
    <div className={`glass-card border ${statusColors[status]} overflow-hidden group hover:border-opacity-60 transition-all duration-300`}>
      {/* Camera View */}
      <div className="relative aspect-video bg-[#050a14]">
        {/* Grid */}
        <div className="absolute inset-0 grid-bg opacity-30" />

        {/* Scanlines */}
        <div
          className="absolute inset-0 pointer-events-none opacity-20"
          style={{
            backgroundImage:
              'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(34,211,238,0.01) 3px, rgba(34,211,238,0.01) 4px)',
          }}
        />

        {/* Detection Boxes */}
        {status !== 'offline' &&
          boxes.map((box, i) => {
            const borderCol =
              box.color === 'red'
                ? 'border-red-400'
                : box.color === 'amber'
                ? 'border-amber-400'
                : 'border-cyan-400'
            const bgCol =
              box.color === 'red'
                ? 'bg-red-500'
                : box.color === 'amber'
                ? 'bg-amber-500'
                : 'bg-cyan-500'
            const textCol =
              box.color === 'red'
                ? 'text-red-400'
                : box.color === 'amber'
                ? 'text-amber-400'
                : 'text-cyan-400'
            return (
              <div
                key={i}
                className={`absolute border ${borderCol}`}
                style={{
                  left: `${box.x}%`,
                  top: `${box.y}%`,
                  width: `${box.w}%`,
                  height: `${box.h}%`,
                }}
              >
                <div
                  className={`absolute -top-4 left-0 ${bgCol}/80 text-white text-[8px] px-1 py-0.5 text-mono rounded-sm whitespace-nowrap`}
                >
                  {box.label}
                </div>
                <div className={`absolute top-0 left-0 w-2 h-2 border-t border-l ${borderCol}`} />
                <div className={`absolute top-0 right-0 w-2 h-2 border-t border-r ${borderCol}`} />
                <div className={`absolute bottom-0 left-0 w-2 h-2 border-b border-l ${borderCol}`} />
                <div className={`absolute bottom-0 right-0 w-2 h-2 border-b border-r ${borderCol}`} />
              </div>
            )
          })}

        {/* Offline overlay */}
        {status === 'offline' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/60">
            <WifiOff className="w-6 h-6 text-slate-500" />
            <span className="text-xs text-mono text-slate-500">SIGNAL LOST</span>
          </div>
        )}

        {/* Top HUD */}
        <div className="absolute top-1.5 left-2 right-2 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className={`status-dot ${dotColors[status]}`} />
            <span className="text-[9px] text-mono text-slate-300">{id}</span>
          </div>
          {status !== 'offline' && (
            <span className="text-[9px] text-mono text-slate-500">{timeStr}</span>
          )}
        </div>

        {/* Bottom HUD */}
        {status !== 'offline' && (
          <div className="absolute bottom-0 left-0 right-0 bg-black/50 px-2 py-1 flex items-center justify-between">
            <span className="text-[8px] text-mono text-cyan-400/60">
              {status === 'alert' ? '⚠ ALERT' : 'REC ●'}
            </span>
            <span className="text-[8px] text-mono text-slate-500">{fps}fps</span>
          </div>
        )}

        {/* Alert flash */}
        {status === 'alert' && (
          <div className="absolute inset-0 border-2 border-red-500/50 rounded pointer-events-none animate-pulse-slow" />
        )}

        {/* Expand icon on hover */}
        <button className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-white bg-black/40 rounded p-0.5">
          <Maximize2 className="w-3 h-3" />
        </button>
      </div>

      {/* Footer */}
      <div className="px-3 py-2 flex items-center justify-between">
        <span className="text-xs text-slate-400 font-medium truncate">{label}</span>
        {alerts > 0 && (
          <div className="flex items-center gap-1 text-red-400 text-[10px] text-mono">
            <AlertTriangle className="w-3 h-3" />
            {alerts}
          </div>
        )}
      </div>
    </div>
  )
}

export default CameraFeed
