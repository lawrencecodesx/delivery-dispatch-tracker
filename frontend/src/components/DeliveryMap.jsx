import { useEffect } from 'react'
import { divIcon } from 'leaflet'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet'

const DEFAULT_CENTER = [5.6037, -0.187]
const PIN_ICONS = {
  pickup: divIcon({
    className: 'delivery-map-pin pickup-pin',
    html: '<span></span>',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  }),
  destination: divIcon({
    className: 'delivery-map-pin destination-pin',
    html: '<span></span>',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  }),
  rider: divIcon({
    className: 'delivery-map-pin rider-pin',
    html: '<span></span>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  }),
}

function MapViewport({ points }) {
  const map = useMap()

  useEffect(() => {
    const validPoints = points.filter(Boolean)
    if (validPoints.length > 1) {
      map.fitBounds(validPoints, { padding: [32, 32], maxZoom: 14 })
    } else if (validPoints.length === 1) {
      map.setView(validPoints[0], 14)
    }
  }, [map, points])

  return null
}

function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click(event) {
      onMapClick?.({
        latitude: Number(event.latlng.lat.toFixed(6)),
        longitude: Number(event.latlng.lng.toFixed(6)),
      })
    },
  })
  return null
}

export function DeliveryMap({
  markers = [],
  onMapClick,
  className = '',
  zoom = 12,
}) {
  const positions = markers
    .map((marker) => marker.position)
    .filter((position) => Array.isArray(position))
  const center = positions[0] || DEFAULT_CENTER

  return (
    <div className={`delivery-map h-72 overflow-hidden rounded-2xl ${className}`}>
      <MapContainer center={center} zoom={zoom} scrollWheelZoom className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapViewport points={positions} />
        {onMapClick && <MapClickHandler onMapClick={onMapClick} />}
        {markers.map((marker, index) => {
          const icon = PIN_ICONS[marker.type] || PIN_ICONS.destination
          return (
            <Marker key={`${marker.type || 'pin'}-${marker.id ?? index}`} position={marker.position} icon={icon}>
              {marker.label && <Popup>{marker.label}</Popup>}
            </Marker>
          )
        })}
        {positions.length > 1 && <Polyline positions={positions.slice(0, 2)} color="#2563eb" dashArray="7 8" />}
      </MapContainer>
    </div>
  )
}
