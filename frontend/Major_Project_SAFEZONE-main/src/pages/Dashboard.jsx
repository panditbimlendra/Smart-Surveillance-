import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Activity, AlertTriangle, Camera, MapPin, Mic, RefreshCw, Square, Upload } from 'lucide-react'
import DashboardLayout from '../components/DashboardLayout'
import StatCard from '../components/StatCard'
import { analyzeFile, getHealth, getRecentAlerts, getRecentLogs, getStreamFrameUrl, getStreamStatus, startStream, stopStream } from '../lib/api'

const POLL_MS = 5000
const HIGH_RISK_SCORE = 0.7
const ALARM_AUDIO_PATH = '/siren-alert-sound.mp3'

function notificationItems(alertsData) {
  return alertsData.slice(0, 4).map((alert) => ({
    id: alert.id,
    message: alert.message,
    severity:
      alert.severity === 'high'
        ? 'critical'
        : alert.severity === 'medium'
        ? 'warning'
        : 'info',
    time: alert.time,
    read: false,
  }))
}

function isHighRiskResult(result) {
  if (!result) return false

  const riskLevel = String(result.risk_level || '').toUpperCase()
  const riskScore = Number(result.risk_score ?? 0)
  return riskLevel === 'DANGER' || riskScore >= HIGH_RISK_SCORE
}

function isAbnormalResult(result) {
  if (!result) return false
  return String(result.risk_level || '').toUpperCase() !== 'SAFE'
}

async function playAlarmSound(audioContextRef, audioElementRef) {
  try {
    if (!audioElementRef.current) {
      const audio = new Audio(ALARM_AUDIO_PATH)
      audio.preload = 'auto'
      audio.volume = 1
      audioElementRef.current = audio
    }

    const audio = audioElementRef.current
    audio.pause()
    audio.currentTime = 0
    await audio.play()
    return
  } catch (audioError) {
    console.warn('Falling back to generated alarm sound.', audioError)
  }

  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  if (!AudioContextClass) {
    throw new Error('This browser does not support alarm audio.')
  }

  if (!audioContextRef.current) {
    audioContextRef.current = new AudioContextClass()
  }

  const audioContext = audioContextRef.current
  if (audioContext.state === 'suspended') {
    await audioContext.resume()
  }

  const now = audioContext.currentTime
  const masterGain = audioContext.createGain()
  masterGain.gain.setValueAtTime(0.45, now)
  masterGain.connect(audioContext.destination)
  masterGain.gain.exponentialRampToValueAtTime(0.0001, now + 2.8)

  ;[0, 0.45, 0.9, 1.35, 1.8, 2.25].forEach((offset, index) => {
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()

    oscillator.type = 'square'
    oscillator.frequency.setValueAtTime(index % 2 === 0 ? 960 : 720, now + offset)
    oscillator.frequency.exponentialRampToValueAtTime(index % 2 === 0 ? 720 : 960, now + offset + 0.32)

    gainNode.gain.setValueAtTime(0.0001, now + offset)
    gainNode.gain.exponentialRampToValueAtTime(0.8, now + offset + 0.03)
    gainNode.gain.exponentialRampToValueAtTime(0.0001, now + offset + 0.38)

    oscillator.connect(gainNode)
    gainNode.connect(masterGain)
    oscillator.start(now + offset)
    oscillator.stop(now + offset + 0.4)
  })
}

function Dashboard() {
  const [notifications, setNotifications] = useState([])
  const [alerts, setAlerts] = useState([])
  const [logs, setLogs] = useState([])
  const [health, setHealth] = useState(null)
  const [streamStatus, setStreamStatus] = useState(null)
  const [showNotifPanel, setShowNotifPanel] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [cameraId, setCameraId] = useState('cam1')
  const [cameraSource, setCameraSource] = useState('0')
  const [cameraActionState, setCameraActionState] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [analyzeState, setAnalyzeState] = useState('')
  const [analyzeResult, setAnalyzeResult] = useState(null)
  const [isStartingCamera, setIsStartingCamera] = useState(false)
  const [isStoppingCamera, setIsStoppingCamera] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [previewFailed, setPreviewFailed] = useState(false)
  const alarmEnabled = true

  const notifPanelRef = useRef(null)
  const audioContextRef = useRef(null)
  const alarmAudioRef = useRef(null)
  const lastAlarmKeyRef = useRef('')

  useEffect(() => {
    function handleClick(event) {
      if (notifPanelRef.current && !notifPanelRef.current.contains(event.target)) {
        setShowNotifPanel(false)
      }
    }

    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  useEffect(() => {
    if (showNotifPanel) {
      setNotifications((prev) => prev.map((item) => ({ ...item, read: true })))
    }
  }, [showNotifPanel])

  useEffect(() => {
    function unlockAudio() {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext
      if (!AudioContextClass) return

      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContextClass()
      }

      if (audioContextRef.current.state === 'suspended') {
        audioContextRef.current.resume().catch(() => {})
      }
    }

    window.addEventListener('pointerdown', unlockAudio, { passive: true })

    return () => {
      window.removeEventListener('pointerdown', unlockAudio)
    }
  }, [])

  useEffect(() => {
    return () => {
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(() => {})
      }

      if (alarmAudioRef.current) {
        alarmAudioRef.current.pause()
        alarmAudioRef.current.currentTime = 0
      }
    }
  }, [])

  async function refreshOperationalData() {
    const [alertsData, logsData, streamData] = await Promise.all([
      getRecentAlerts(12),
      getRecentLogs(20),
      getStreamStatus(),
    ])

    setAlerts(alertsData)
    setLogs(logsData)
    setStreamStatus(streamData)
    setNotifications(notificationItems(alertsData))
  }

  useEffect(() => {
    let active = true

    async function loadData() {
      try {
        const [healthData, alertsData, logsData, streamData] = await Promise.all([
          getHealth(),
          getRecentAlerts(12),
          getRecentLogs(20),
          getStreamStatus(),
        ])

        if (!active) return

        setHealth(healthData)
        setAlerts(alertsData)
        setLogs(logsData)
        setStreamStatus(streamData)
        setNotifications(notificationItems(alertsData))
        setError('')
      } catch (loadError) {
        if (!active) return
        setError(loadError.message || 'Could not reach backend')
      } finally {
        if (active) setLoading(false)
      }
    }

    loadData()
    const intervalId = setInterval(loadData, POLL_MS)

    return () => {
      active = false
      clearInterval(intervalId)
    }
  }, [])

  const stats = useMemo(() => {
    const criticalAlerts = alerts.filter((alert) => alert.severity === 'high').length
    const liveStream = streamStatus?.streaming ? 1 : 0

    return [
      {
        title: 'Active Camera',
        value: String(liveStream),
        subtitle: streamStatus?.camera_id || 'No stream',
        icon: Camera,
        accentColor: 'cyan',
      },
      {
        title: 'Alerts Today',
        value: String(alerts.length),
        subtitle: `${criticalAlerts} high severity`,
        icon: AlertTriangle,
        accentColor: 'red',
      },
      {
        title: 'Events Synced',
        value: String(logs.length),
        subtitle: `Backend ${health?.status || 'offline'}`,
        icon: Activity,
        accentColor: 'amber',
      },
    ]
  }, [alerts, health, logs, streamStatus])

  const detectionSummary = useMemo(() => {
    const fusion = analyzeResult?.fusion
    if (!fusion) return null

    const audioOnlyDetection =
      analyzeResult?.frames_sampled === 0 &&
      String(fusion.top_audio || '').toLowerCase() !== 'normal'

    const isAbnormal = fusion.risk_level !== 'SAFE' || audioOnlyDetection
    return {
      label: isAbnormal ? 'ABNORMAL ACTIVITY DETECTED' : 'NORMAL ACTIVITY',
      tone: isAbnormal
        ? 'border-red-200 bg-red-50 text-red-800'
        : 'border-emerald-200 bg-emerald-50 text-emerald-800',
    }
  }, [analyzeResult])

  const streamPreviewUrl = useMemo(() => {
    if (!streamStatus?.streaming || !streamStatus?.frames_processed) return ''
    return getStreamFrameUrl(`${streamStatus.frames_processed}-${streamStatus.camera_id || 'cam'}`)
  }, [streamStatus])

  useEffect(() => {
    setPreviewFailed(false)
  }, [streamPreviewUrl, streamStatus?.streaming])

  useEffect(() => {
    const liveResult = streamStatus?.last_result
    if (!alarmEnabled || !isHighRiskResult(liveResult)) return

    const alarmKey = [
      'stream',
      streamStatus?.camera_id || 'none',
      streamStatus?.clips_processed || 0,
      liveResult?.risk_level || 'SAFE',
      Number(liveResult?.risk_score ?? 0).toFixed(3),
    ].join(':')

    if (lastAlarmKeyRef.current === alarmKey) return

    lastAlarmKeyRef.current = alarmKey
    playAlarmSound(audioContextRef, alarmAudioRef)
      .then(() => {
      })
      .catch(() => {})
  }, [alarmEnabled, streamStatus])

  useEffect(() => {
    const uploadResult = analyzeResult?.fusion
    if (!alarmEnabled || !isAbnormalResult(uploadResult)) return

    const alarmKey = [
      'upload',
      analyzeResult?.filename || 'file',
      uploadResult?.risk_level || 'SAFE',
      Number(uploadResult?.risk_score ?? 0).toFixed(3),
    ].join(':')

    if (lastAlarmKeyRef.current === alarmKey) return

    lastAlarmKeyRef.current = alarmKey
    playAlarmSound(audioContextRef, alarmAudioRef)
      .then(() => {
      })
      .catch(() => {})
  }, [alarmEnabled, analyzeResult])

  async function handleStartCamera() {
    try {
      setIsStartingCamera(true)
      setCameraActionState('Starting camera...')
      await startStream({ rtsp_url: cameraSource, camera_id: cameraId })
      const status = await getStreamStatus()
      setStreamStatus(status)
      setCameraActionState(
        status.streaming
          ? `Camera started: ${status.camera_id || cameraId}`
          : status.error_message || 'Camera did not stay connected'
      )
    } catch (cameraError) {
      setCameraActionState(cameraError.message || 'Could not start camera')
    } finally {
      setIsStartingCamera(false)
    }
  }

  async function handleStopCamera() {
    try {
      setIsStoppingCamera(true)
      setCameraActionState('Stopping camera...')
      await stopStream()
      const status = await getStreamStatus()
      setStreamStatus(status)
      setCameraActionState('Camera stopped')
    } catch (cameraError) {
      setCameraActionState(cameraError.message || 'Could not stop camera')
    } finally {
      setIsStoppingCamera(false)
    }
  }

  async function handleAnalyzeUpload() {
    if (!selectedFile) {
      setAnalyzeState('Choose a video or audio file first')
      return
    }

    try {
      setIsAnalyzing(true)
      setAnalyzeState('Uploading for analysis...')
      const result = await analyzeFile(selectedFile)
      setAnalyzeResult(result)
      await refreshOperationalData()
      const audioOnlyDetection =
        result.frames_sampled === 0 &&
        String(result.fusion?.top_audio || '').toLowerCase() !== 'normal'
      const detectionLabel =
        audioOnlyDetection
          ? result.fusion?.top_audio
          : result.fusion?.risk_level

      setAnalyzeState(
        result.fusion?.risk_level === 'SAFE' && !audioOnlyDetection
          ? 'Detection complete: normal activity'
          : `Detection complete: ${detectionLabel || 'abnormal activity'}`
      )
    } catch (uploadError) {
      setAnalyzeState(uploadError.message || 'Analysis failed')
      setAnalyzeResult(null)
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <DashboardLayout
      notifications={notifications}
      onBellClick={() => setShowNotifPanel((prev) => !prev)}
      showNotifPanel={showNotifPanel}
      notifPanelRef={notifPanelRef}
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2 text-sm text-mono text-slate-700">
          <span className={`w-1.5 h-1.5 rounded-full ${health?.status === 'ok' ? 'bg-emerald-500' : 'bg-red-500'}`} />
          {health?.status === 'ok' ? 'Backend connected' : 'Backend offline'}
          {health?.device ? ` · ${health.device}` : ''}
        </div>
        <div className="text-sm text-slate-600 font-mono flex items-center gap-2">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          {error || 'Auto-refresh every 5s'}
        </div>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {stats.map((stat) => <StatCard key={stat.title} {...stat} />)}
      </div>

      <div className="grid xl:grid-cols-2 gap-4 mb-6">
        <div className="glass-card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-mono px-2 py-1 rounded border ${
                streamStatus?.streaming
                  ? 'bg-red-100 text-red-700 border-red-200'
                  : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}>
                {streamStatus?.streaming ? 'LIVE' : 'IDLE'}
              </span>
              <span className="text-sm text-slate-900 font-semibold">
                {streamStatus?.camera_id || 'No camera connected'}
              </span>
            </div>
            <span className="text-sm font-mono text-slate-500">
              {streamStatus?.rtsp_url || 'No stream source'}
            </span>
          </div>

          <div className="aspect-video bg-slate-100 flex items-center justify-center border-b border-slate-200 overflow-hidden">
            {streamStatus?.streaming && streamPreviewUrl && !previewFailed ? (
              <img
                src={streamPreviewUrl}
                alt="Live camera preview"
                className="h-full w-full object-cover"
                onError={() => setPreviewFailed(true)}
              />
            ) : (
              <div className="text-center px-6">
              <Camera className="w-12 h-12 text-slate-500 mx-auto mb-3" />
              <p className="text-sm text-slate-700 font-mono">
                {streamStatus?.streaming
                  ? streamStatus?.frames_processed
                    ? 'Live preview temporarily unavailable'
                    : 'Starting camera feed. Waiting for first frame...'
                  : 'Start the camera to view live status'}
              </p>
              {streamStatus?.error_message && (
                <p className="text-sm text-red-700 mt-2 font-mono">
                  {streamStatus.error_message}
                </p>
              )}
              {streamStatus?.last_result && (
                <p className="text-sm text-sky-700 mt-2 font-mono">
                  {streamStatus.last_result.risk_level} · {streamStatus.last_result.top_video}
                </p>
              )}
              </div>
            )}
          </div>

          <div className="px-4 py-3 text-sm text-slate-700 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <MapPin className="w-3 h-3 text-sky-700" />
              {streamStatus?.camera_id || 'No zone'}
            </span>
            <span>{streamStatus?.frames_processed || 0} frames processed</span>
          </div>
        </div>

        <div className="glass-card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
            <div className="flex items-center gap-2">
              <Mic className="w-4 h-4 text-sky-700" />
              <span className="text-sm text-slate-900 font-semibold">Latest Fusion Result</span>
            </div>
            <span className="text-sm font-mono text-slate-500">
              {streamStatus?.last_alert_ts ? 'Alert sent recently' : 'No recent alert'}
            </span>
          </div>

          <div className="p-5 space-y-4 bg-white">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">Risk Level</p>
                <p className="text-lg text-slate-900 font-semibold">
                  {streamStatus?.last_result?.risk_level || 'SAFE'}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">Risk Score</p>
                <p className="text-lg text-slate-900 font-semibold">
                  {Number(streamStatus?.last_result?.risk_score ?? 0).toFixed(4)}
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Top video label</span>
                <span className="text-sky-700 font-mono">
                  {streamStatus?.last_result?.top_video || 'normal'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Top audio label</span>
                <span className="text-sky-700 font-mono">
                  {streamStatus?.last_result?.top_audio || 'normal'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Audio available</span>
                <span className="text-slate-900 font-mono">
                  {streamStatus?.last_result?.audio_conf != null ? 'yes' : 'no'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid xl:grid-cols-2 gap-4 mb-6">
        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Camera className="w-4 h-4 text-sky-700" />
            <h2 className="text-sm font-semibold text-slate-900">Camera Controls</h2>
          </div>

          <div className="grid sm:grid-cols-2 gap-3 mb-4">
            <div>
              <label className="block text-sm text-slate-600 mb-1">Camera ID</label>
              <input
                value={cameraId}
                onChange={(event) => setCameraId(event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-sky-400"
                placeholder="cam1"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-600 mb-1">RTSP URL or webcam index</label>
              <input
                value={cameraSource}
                onChange={(event) => setCameraSource(event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-sky-400"
                placeholder="0"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleStartCamera}
              disabled={isStartingCamera}
              className="inline-flex items-center gap-2 rounded-xl bg-sky-700 px-4 py-2 text-sm font-medium text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Camera className="w-4 h-4" />
              {isStartingCamera ? 'Starting...' : 'Start Camera'}
            </button>
            <button
              onClick={handleStopCamera}
              disabled={isStoppingCamera}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Square className="w-4 h-4" />
              {isStoppingCamera ? 'Stopping...' : 'Stop Camera'}
            </button>
          </div>

          <p className="mt-3 text-sm text-slate-600">{cameraActionState || 'Use 0 for your default webcam.'}</p>
        </div>

        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Upload className="w-4 h-4 text-sky-700" />
            <h2 className="text-sm font-semibold text-slate-900">Upload Video or Audio</h2>
          </div>

          <div className="space-y-3">
            <input
              type="file"
              accept=".mp4,.avi,.mkv,.mov,.mp3,.wav,.flac,.m4a,.aac,.ogg,.opus,.wma"
              onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
              className="block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
            />

            <button
              onClick={handleAnalyzeUpload}
              disabled={isAnalyzing}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Upload className="w-4 h-4" />
              {isAnalyzing ? 'Detecting...' : 'Detect Activity'}
            </button>

            <p className="text-sm text-slate-600">{analyzeState || 'Upload a media file for direct backend detection.'}</p>

            {analyzeResult && (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-800 space-y-2">
                {detectionSummary && (
                  <div className={`rounded-xl border px-3 py-2 text-center text-sm font-semibold tracking-widest ${detectionSummary.tone}`}>
                    {detectionSummary.label}
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">File</span>
                  <span className="font-mono">{analyzeResult.filename}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Risk level</span>
                  <span className="font-semibold">{analyzeResult.fusion?.risk_level}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Risk score</span>
                  <span className="font-mono">{Number(analyzeResult.fusion?.risk_score ?? 0).toFixed(4)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Top video</span>
                  <span className="font-mono">{analyzeResult.fusion?.top_video}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Top audio</span>
                  <span className="font-mono">{analyzeResult.fusion?.top_audio}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Frames sampled</span>
                  <span className="font-mono">{analyzeResult.frames_sampled}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Audio available</span>
                  <span className="font-mono">{analyzeResult.audio_available ? 'yes' : 'no'}</span>
                </div>
                {analyzeResult.duration_secs != null && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Duration</span>
                    <span className="font-mono">{Number(analyzeResult.duration_secs).toFixed(2)} s</span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Processing time</span>
                  <span className="font-mono">{analyzeResult.processing_ms} ms</span>
                </div>
                {Array.isArray(analyzeResult.audio_detections) && analyzeResult.audio_detections.length > 0 && (
                  <div className="pt-3 border-t border-slate-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-slate-500">Audio detections</span>
                      <span className="font-mono">{analyzeResult.audio_detections.length}</span>
                    </div>
                    <div className="space-y-2">
                      {analyzeResult.audio_detections.slice(0, 6).map((detection, index) => (
                        <div
                          key={`${detection.label_key}-${detection.start_time}-${index}`}
                          className="rounded-lg border border-slate-200 bg-white px-3 py-2"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-medium">{detection.label}</span>
                            <span className="font-mono text-xs">
                              {(Number(detection.confidence) * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="mt-1 text-xs text-slate-500 font-mono">
                            {Number(detection.start_time).toFixed(1)}s - {Number(detection.end_time).toFixed(1)}s
                            {' · '}
                            {detection.severity}
                          </div>
                        </div>
                      ))}
                      {analyzeResult.audio_detections.length > 6 && (
                        <p className="text-xs text-slate-500 font-mono">
                          Showing first 6 detections
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between gap-3 mb-4">
          <h2 className="text-sm font-semibold text-slate-900 text-display tracking-widest uppercase">
            Event Log
          </h2>
          <span className="text-sm font-mono text-slate-500">
            {logs.length} recent records
          </span>
        </div>

        <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
          {logs.length === 0 ? (
            <div className="text-center py-12 text-sm text-slate-600 font-mono">
              No backend logs available yet.
            </div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className="flex items-center gap-4 px-4 py-3 rounded-xl border border-slate-200 bg-white"
              >
                <span className="text-xs font-mono text-slate-500 w-20">{log.time}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-900 font-medium truncate">{log.event}</p>
                  <p className="text-xs text-slate-500 truncate">{log.zone}</p>
                </div>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-100 text-sky-700">
                  {log.type}
                </span>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                  {log.status}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}

export default Dashboard
