export const cameraLocations = {
  cam1: {
    id: 'cam1',
    label: 'SafeZone Camera 1',
    lat: 27.7172,
    lng: 85.324,
    area: 'Kathmandu Control Zone',
  },
  CAM_01: {
    id: 'CAM_01',
    label: 'Main Entrance',
    lat: 27.7174,
    lng: 85.3242,
    area: 'Main Entrance',
  },
  CAM_02: {
    id: 'CAM_02',
    label: 'Lobby Zone A',
    lat: 27.7171,
    lng: 85.3245,
    area: 'Lobby',
  },
  CAM_03: {
    id: 'CAM_03',
    label: 'Gate A',
    lat: 27.7169,
    lng: 85.3237,
    area: 'Gate A',
  },
  CAM_07: {
    id: 'CAM_07',
    label: 'Zone B Sector 4',
    lat: 27.7178,
    lng: 85.3248,
    area: 'Zone B',
  },
  CAM_09: {
    id: 'CAM_09',
    label: 'Rooftop Zone',
    lat: 27.7181,
    lng: 85.3241,
    area: 'Rooftop',
  },
  SYS: {
    id: 'SYS',
    label: 'System Core',
    lat: 27.7172,
    lng: 85.324,
    area: 'Control Centre',
  },
}

export function getCameraLocation(cameraId) {
  return cameraLocations[cameraId] || cameraLocations.cam1
}

export function buildMapEmbedUrl(lat, lng, delta = 0.01) {
  const left = lng - delta
  const right = lng + delta
  const top = lat + delta
  const bottom = lat - delta
  return `https://www.openstreetmap.org/export/embed.html?bbox=${left}%2C${bottom}%2C${right}%2C${top}&layer=mapnik&marker=${lat}%2C${lng}`
}
