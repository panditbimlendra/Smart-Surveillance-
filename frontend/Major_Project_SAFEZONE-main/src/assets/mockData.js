export const mockAlerts = [
  {
    id: 1,
    type: 'Intrusion Detected',
    message: 'Unauthorized person detected in restricted Zone B',
    location: 'Zone B — Sector 4',
    camera: 'CAM_07',
    time: '23:41',
    severity: 'high',
  },
  {
    id: 2,
    type: 'Audio Anomaly',
    message: 'Loud impact sound detected — possible glass break',
    location: 'Building C — Floor 2',
    camera: 'MIC_03',
    time: '23:38',
    severity: 'high',
  },
  {
    id: 3,
    type: 'Suspicious Activity',
    message: 'Individual loitering near entrance for 15+ minutes',
    location: 'Main Entrance',
    camera: 'CAM_01',
    time: '23:22',
    severity: 'medium',
  },
  {
    id: 4,
    type: 'Object Left Behind',
    message: 'Unattended package detected in lobby area',
    location: 'Lobby — Zone A',
    camera: 'CAM_02',
    time: '23:15',
    severity: 'medium',
  },
  {
    id: 5,
    type: 'Motion Detected',
    message: 'Movement detected in parking lot after hours',
    location: 'Parking Lot',
    camera: 'CAM_12',
    time: '22:59',
    severity: 'low',
  },
  {
    id: 6,
    type: 'Camera Offline',
    message: 'CAM_09 connection lost — auto-failover activated',
    location: 'Rooftop Zone',
    camera: 'CAM_09',
    time: '22:47',
    severity: 'medium',
  },
 

]

export const mockLogs = [
  { id: 1, time: '23:41:07', event: 'Intrusion Alert', zone: 'Zone B', camera: 'CAM_07', type: 'THREAT', status: 'ACTIVE' },
  { id: 2, time: '23:38:42', event: 'Audio Alert', zone: 'Building C', camera: 'MIC_03', type: 'AUDIO', status: 'ACTIVE' },
  { id: 3, time: '23:22:11', event: 'Loitering Detected', zone: 'Main Entrance', camera: 'CAM_01', type: 'BEHAVIOR', status: 'REVIEW' },
  { id: 4, time: '23:15:33', event: 'Unattended Object', zone: 'Lobby', camera: 'CAM_02', type: 'OBJECT', status: 'REVIEW' },
  { id: 5, time: '22:59:05', event: 'Motion Event', zone: 'Parking Lot', camera: 'CAM_12', type: 'MOTION', status: 'LOGGED' },
  { id: 6, time: '22:47:18', event: 'Camera Offline', zone: 'Rooftop', camera: 'CAM_09', type: 'SYSTEM', status: 'RESOLVED' },
  { id: 7, time: '22:30:00', event: 'Access Event', zone: 'Server Room', camera: 'CAM_05', type: 'ACCESS', status: 'RESOLVED' },
  { id: 8, time: '22:00:00', event: 'System Diagnostics', zone: 'ALL', camera: 'SYS', type: 'SYSTEM', status: 'RESOLVED' },
  { id: 9, time: '21:45:22', event: 'Person Detected', zone: 'Zone C', camera: 'CAM_11', type: 'OBJECT', status: 'LOGGED' },
  { id: 10, time: '21:30:15', event: 'Vehicle Entry', zone: 'Gate A', camera: 'CAM_03', type: 'MOTION', status: 'LOGGED' },
  { id: 11, time: '21:15:08', event: 'Crowd Detected', zone: 'Zone A', camera: 'CAM_02', type: 'BEHAVIOR', status: 'LOGGED' },
  { id: 12, time: '21:00:00', event: 'AI Model Updated', zone: 'SYSTEM', camera: 'SYS', type: 'SYSTEM', status: 'RESOLVED' },
]

export const mockCameras = [
  { id: 'CAM_01', label: 'Main Entrance', status: 'online', alerts: 1, fps: 30 },
  { id: 'CAM_02', label: 'Lobby Zone A', status: 'online', alerts: 1, fps: 30 },
  { id: 'CAM_03', label: 'Gate A', status: 'online', alerts: 0, fps: 25 },
  { id: 'CAM_04', label: 'Corridor B', status: 'online', alerts: 0, fps: 30 },
  { id: 'CAM_05', label: 'Server Room', status: 'online', alerts: 0, fps: 30 },
  { id: 'CAM_06', label: 'Emergency Exit', status: 'online', alerts: 0, fps: 25 },
  { id: 'CAM_07', label: 'Zone B Sector 4', status: 'alert', alerts: 1, fps: 30 },
  { id: 'CAM_08', label: 'Loading Dock', status: 'online', alerts: 0, fps: 25 },
  { id: 'CAM_09', label: 'Rooftop Zone', status: 'offline', alerts: 0, fps: 0 },
]

export const mapZones = [
  { id: 1, x: 20, y: 15, label: 'Zone A', status: 'clear', cameras: 3 },
  { id: 2, x: 55, y: 20, label: 'Zone B', status: 'alert', cameras: 2 },
  { id: 3, x: 75, y: 45, label: 'Zone C', status: 'clear', cameras: 4 },
  { id: 4, x: 35, y: 60, label: 'Zone D', status: 'clear', cameras: 2 },
  { id: 5, x: 10, y: 75, label: 'Parking', status: 'warning', cameras: 3 },
  { id: 6, x: 65, y: 75, label: 'Building C', status: 'alert', cameras: 2 },
]
