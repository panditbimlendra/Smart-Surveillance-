import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Crosshair, ExternalLink, MapPin, Navigation, Radio, RefreshCw } from 'lucide-react'
import DashboardLayout from '../components/DashboardLayout'
import { getRecentAlerts, getRecentLogs, getStreamStatus } from '../lib/api'
import { getCameraLocation } from '../lib/cameraLocations'

const LEAFLET_CSS_ID = 'safezone-leaflet-css'
const LEAFLET_SCRIPT_ID = 'safezone-leaflet-script'

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

function toRadians(value) {
  return (value * Math.PI) / 180
}

function calculateDistanceKm(a, b) {
  const earthRadiusKm = 6371
  const dLat = toRadians(b.lat - a.lat)
  const dLng = toRadians(b.lng - a.lng)
  const startLat = toRadians(a.lat)
  const endLat = toRadians(b.lat)

  const haversine =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(startLat) * Math.cos(endLat) * Math.sin(dLng / 2) ** 2

  return 2 * earthRadiusKm * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine))
}

function loadLeaflet() {
  if (window.L) {
    return Promise.resolve(window.L)
  }

  return new Promise((resolve, reject) => {
    let cssTag = document.getElementById(LEAFLET_CSS_ID)
    if (!cssTag) {
      cssTag = document.createElement('link')
      cssTag.id = LEAFLET_CSS_ID
      cssTag.rel = 'stylesheet'
      cssTag.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
      document.head.appendChild(cssTag)
    }

    const existingScript = document.getElementById(LEAFLET_SCRIPT_ID)
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(window.L), { once: true })
      existingScript.addEventListener('error', () => reject(new Error('Leaflet failed to load.')), { once: true })
      return
    }

    const scriptTag = document.createElement('script')
    scriptTag.id = LEAFLET_SCRIPT_ID
    scriptTag.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    scriptTag.async = true
    scriptTag.onload = () => resolve(window.L)
    scriptTag.onerror = () => reject(new Error('Leaflet failed to load.'))
    document.body.appendChild(scriptTag)
  })
}

function createCameraIcon(L) {
  return L.divIcon({
    className: '',
    html: `
      <div style="display:flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:9999px;background:#0369a1;border:3px solid #ffffff;box-shadow:0 10px 20px rgba(3,105,161,0.35);">
        <span style="display:block;width:10px;height:10px;border-radius:9999px;background:#e0f2fe;"></span>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -16],
  })
}

function createLiveIcon(L) {
  return L.divIcon({
    className: '',
    html: `
      <div style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:9999px;background:#059669;border:3px solid #ffffff;box-shadow:0 10px 20px rgba(5,150,105,0.35);">
        <span style="display:block;width:8px;height:8px;border-radius:9999px;background:#d1fae5;"></span>
      </div>
    `,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -16],
  })
}

function MapView() {
  const [notifications, setNotifications] = useState([])
  const [alerts, setAlerts] = useState([])
  const [logs, setLogs] = useState([])
  const [streamStatus, setStreamStatus] = useState(null)
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(true)
  const [liveLocation, setLiveLocation] = useState(null)
  const [locationLoading, setLocationLoading] = useState(false)
  const [locationError, setLocationError] = useState('')
  const [mapReady, setMapReady] = useState(false)
  const [mapError, setMapError] = useState('')
  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const layerGroupRef = useRef(null)

  useEffect(() => {
    let active = true

    async function loadMapData() {
      try {
        const [alertData, logData, streamData] = await Promise.all([
          getRecentAlerts(20),
          getRecentLogs(20),
          getStreamStatus(),
        ])

        if (!active) return

        setAlerts(alertData)
        setLogs(logData)
        setStreamStatus(streamData)
        setNotifications(notificationItems(alertData))

        const defaultId =
          streamData?.camera_id ||
          alertData[0]?.camera ||
          logData[0]?.camera ||
          'cam1'

        setSelectedId((prev) => prev || defaultId)
      } catch (error) {
        console.error('Failed to load map data', error)
      } finally {
        if (active) setLoading(false)
      }
    }

    loadMapData()

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    requestLiveLocation()
  }, [])

  useEffect(() => {
    let cancelled = false

    async function setupMap() {
      try {
        const L = await loadLeaflet()
        if (cancelled || !mapContainerRef.current || mapRef.current) return

        const map = L.map(mapContainerRef.current, {
          zoomControl: true,
          attributionControl: true,
        }).setView([27.7172, 85.324], 15)

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map)

        mapRef.current = map
        layerGroupRef.current = L.layerGroup().addTo(map)
        setMapReady(true)
      } catch (error) {
        console.error('Failed to initialize map', error)
        setMapError('Map tiles could not be loaded right now.')
      }
    }

    setupMap()

    return () => {
      cancelled = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
      layerGroupRef.current = null
    }
  }, [])

  const incidentItems = useMemo(() => {
    const alertItems = alerts.map((alert) => ({
      id: `alert-${alert.id}`,
      camera: alert.camera,
      label: alert.type,
      detail: alert.message,
      severity: alert.severity,
      time: alert.time,
    }))

    const logItems = logs.map((log) => ({
      id: `log-${log.id}`,
      camera: log.camera,
      label: log.event,
      detail: `${log.type} - ${log.status}`,
      severity: log.status === 'ACTIVE' ? 'high' : log.status === 'REVIEW' ? 'medium' : 'low',
      time: log.time,
    }))

    return [...alertItems, ...logItems]
  }, [alerts, logs])

  const selectedIncident =
    incidentItems.find((item) => item.id === selectedId) ||
    incidentItems.find((item) => item.camera === selectedId) ||
    null

  const selectedCameraId = selectedIncident?.camera || selectedId || 'cam1'
  const cameraLocation = getCameraLocation(selectedCameraId)
  const mapsLink = `https://www.openstreetmap.org/?mlat=${cameraLocation.lat}&mlon=${cameraLocation.lng}#map=17/${cameraLocation.lat}/${cameraLocation.lng}`

  const distanceFromLive = useMemo(() => {
    if (!liveLocation) return null
    return calculateDistanceKm(liveLocation, cameraLocation).toFixed(2)
  }, [cameraLocation, liveLocation])

  useEffect(() => {
    if (!mapReady || !mapRef.current || !layerGroupRef.current || !window.L) return

    const L = window.L
    const map = mapRef.current
    const layerGroup = layerGroupRef.current
    layerGroup.clearLayers()

    const bounds = []

    const cameraMarker = L.marker([cameraLocation.lat, cameraLocation.lng], {
      icon: createCameraIcon(L),
    }).bindPopup(`
      <div style="min-width:180px;">
        <strong>${cameraLocation.label}</strong><br/>
        ${cameraLocation.area}<br/>
        Camera ID: ${cameraLocation.id}
      </div>
    `)
    cameraMarker.addTo(layerGroup)
    bounds.push([cameraLocation.lat, cameraLocation.lng])

    if (selectedIncident) {
      cameraMarker.openPopup()
    }

    if (liveLocation) {
      const liveMarker = L.marker([liveLocation.lat, liveLocation.lng], {
        icon: createLiveIcon(L),
      }).bindPopup(`
        <div style="min-width:180px;">
          <strong>${liveLocation.label}</strong><br/>
          ${liveLocation.area}<br/>
          Accuracy: +/- ${liveLocation.accuracy} m
        </div>
      `)
      liveMarker.addTo(layerGroup)

      L.circle([liveLocation.lat, liveLocation.lng], {
        radius: Math.max(liveLocation.accuracy || 0, 25),
        color: '#059669',
        fillColor: '#6ee7b7',
        fillOpacity: 0.18,
        weight: 1.5,
      }).addTo(layerGroup)

      bounds.push([liveLocation.lat, liveLocation.lng])
    }

    if (bounds.length > 1) {
      map.fitBounds(bounds, { padding: [50, 50] })
    } else if (bounds.length === 1) {
      map.setView(bounds[0], 16)
    }
  }, [cameraLocation, liveLocation, mapReady, selectedIncident])

  function requestLiveLocation() {
    if (!navigator.geolocation) {
      setLocationError('Browser location is not available on this device.')
      return
    }

    setLocationLoading(true)
    setLocationError('')

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLiveLocation({
          id: 'live-location',
          label: 'Your Live Location',
          area: 'Browser Geolocation',
          lat: Number(position.coords.latitude.toFixed(6)),
          lng: Number(position.coords.longitude.toFixed(6)),
          accuracy: Math.round(position.coords.accuracy || 0),
        })
        setLocationLoading(false)
      },
      (error) => {
        const messages = {
          1: 'Location permission was denied.',
          2: 'Current location could not be determined.',
          3: 'Location request timed out.',
        }
        setLocationError(messages[error.code] || 'Could not fetch live location.')
        setLocationLoading(false)
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000,
      }
    )
  }

  function focusCamera() {
    if (!mapRef.current) return
    mapRef.current.setView([cameraLocation.lat, cameraLocation.lng], 17)
  }

  function focusLiveLocation() {
    if (!mapRef.current || !liveLocation) return
    mapRef.current.setView([liveLocation.lat, liveLocation.lng], 17)
  }

  return (
    <DashboardLayout
      notifications={notifications}
      onBellClick={() => {}}
      showNotifPanel={false}
      notifPanelRef={null}
    >
      <div className="grid xl:grid-cols-4 gap-4">
        <div className="xl:col-span-3">
          <div className="glass-card overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
              <div className="flex items-center gap-2 text-sm font-mono text-slate-600">
                <MapPin className="w-4 h-4 text-sky-600" />
                {cameraLocation.area}
              </div>

              <div className="flex items-center gap-2 flex-wrap justify-end">
                <button
                  onClick={focusCamera}
                  className="rounded-lg px-3 py-1.5 text-sm font-medium transition bg-sky-100 text-sky-800 hover:bg-sky-200"
                >
                  Focus Camera
                </button>
                <button
                  onClick={focusLiveLocation}
                  disabled={!liveLocation}
                  className="rounded-lg px-3 py-1.5 text-sm font-medium transition bg-emerald-100 text-emerald-800 hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Focus Live Location
                </button>
                <div className="flex items-center gap-2 text-sm font-mono text-slate-500">
                  <RefreshCw className={`w-4 h-4 ${loading || locationLoading ? 'animate-spin' : ''}`} />
                  Real-world map
                </div>
              </div>
            </div>

            <div className="bg-slate-100 p-3">
              {mapError ? (
                <div className="flex h-[520px] items-center justify-center rounded-xl border border-slate-200 bg-white px-6 text-center text-slate-500">
                  {mapError}
                </div>
              ) : (
                <div
                  ref={mapContainerRef}
                  className="h-[520px] w-full rounded-xl border border-slate-200 bg-white"
                />
              )}
            </div>

            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 text-sm gap-3 flex-wrap">
              <div className="text-slate-600">
                Showing camera and live location markers together on the same map.
              </div>
              <a
                href={mapsLink}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-sky-700 hover:text-sky-900"
              >
                Open selected camera in full map
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="glass-card p-4">
            <h3 className="text-base text-display font-semibold text-slate-900 mb-3 tracking-wide">Live Camera</h3>
            <div className="rounded-xl border border-slate-200 bg-white p-3 space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Status</span>
                <span className={`${streamStatus?.streaming ? 'text-emerald-700' : 'text-slate-500'} font-mono`}>
                  {streamStatus?.streaming ? 'CONNECTED' : 'IDLE'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Camera ID</span>
                <span className="text-slate-900 font-mono">{streamStatus?.camera_id || 'none'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Frames</span>
                <span className="text-slate-900 font-mono">{streamStatus?.frames_processed || 0}</span>
              </div>
            </div>
          </div>

          <div className="glass-card p-4">
            <h3 className="text-base text-display font-semibold text-slate-900 mb-3 tracking-wide">Incident Locations</h3>
            <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
              {incidentItems.length === 0 ? (
                <div className="text-sm text-slate-500">No incidents available yet.</div>
              ) : (
                incidentItems.map((item) => {
                  const itemLocation = getCameraLocation(item.camera)
                  const active = item.id === selectedId || (!selectedId && item.camera === selectedCameraId)
                  const severityClasses =
                    item.severity === 'high'
                      ? 'border-red-200 bg-red-50 text-red-700'
                      : item.severity === 'medium'
                      ? 'border-amber-200 bg-amber-50 text-amber-700'
                      : 'border-emerald-200 bg-emerald-50 text-emerald-700'

                  return (
                    <button
                      key={item.id}
                      onClick={() => setSelectedId(item.id)}
                      className={`w-full text-left rounded-xl border p-3 transition ${
                        active ? 'border-sky-300 bg-sky-50' : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-slate-900 truncate">{item.label}</p>
                          <p className="text-sm text-slate-600 mt-1">{item.detail}</p>
                        </div>
                        <span className={`text-xs font-mono px-2 py-1 rounded border ${severityClasses}`}>
                          {item.severity.toUpperCase()}
                        </span>
                      </div>
                      <div className="flex items-center justify-between mt-3 text-xs text-slate-500 font-mono gap-2">
                        <span>{itemLocation.label}</span>
                        <span>{item.time}</span>
                      </div>
                    </button>
                  )
                })
              )}
            </div>
          </div>

          <div className="glass-card p-4">
            <h3 className="text-base text-display font-semibold text-slate-900 mb-3 tracking-wide">Selected Camera Coordinates</h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-slate-700">
                <Radio className="w-4 h-4 text-sky-600" />
                {cameraLocation.label}
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-3 font-mono text-slate-700">
                <p>Lat: {cameraLocation.lat}</p>
                <p>Lng: {cameraLocation.lng}</p>
              </div>
              <p className="text-slate-500">
                Incident markers are linked to the configured camera coordinates.
              </p>
            </div>
          </div>

          <div className="glass-card p-4">
            <h3 className="text-base text-display font-semibold text-slate-900 mb-3 tracking-wide">Live Location</h3>
            <div className="rounded-xl border border-slate-200 bg-white p-3 space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-500">Browser GPS</span>
                <button
                  onClick={requestLiveLocation}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-sky-700 hover:bg-sky-50"
                >
                  <Crosshair className="w-4 h-4" />
                  Refresh
                </button>
              </div>

              {locationLoading ? (
                <p className="text-slate-500">Fetching your live location...</p>
              ) : liveLocation ? (
                <>
                  <div className="flex items-center gap-2 text-slate-700">
                    <Navigation className="w-4 h-4 text-emerald-600" />
                    Your live location is now shown on the map.
                  </div>
                  <div className="font-mono text-slate-700">
                    <p>Lat: {liveLocation.lat}</p>
                    <p>Lng: {liveLocation.lng}</p>
                    <p>Accuracy: +/- {liveLocation.accuracy} m</p>
                  </div>
                  <p className="text-slate-500">
                    Distance from selected camera:{' '}
                    <span className="font-mono text-slate-700">{distanceFromLive || 'n/a'} km</span>
                  </p>
                </>
              ) : (
                <p className="text-slate-500">{locationError || 'Allow location access to link the app with your live location.'}</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}

export default MapView
