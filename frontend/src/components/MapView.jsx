import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'

const DEFAULT_CENTER = [5.6037, -0.187]

export function MapView({
  center = DEFAULT_CENTER,
  marker,
  zoom = 12,
  className = '',
}) {
  const mapCenter = marker || center

  return (
    <div className={`h-80 overflow-hidden rounded-xl border border-slate-200 ${className}`}>
      <MapContainer center={mapCenter} zoom={zoom} scrollWheelZoom className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {marker && (
          <Marker position={marker}>
            <Popup>Latest reported rider location</Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  )
}
