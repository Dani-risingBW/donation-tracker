import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const directionsUrl = location => `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${location.title}, ${location.address}`)}`

const pulseIcon = active => L.divIcon({
  className: active ? 'pulse-marker active' : 'pulse-marker',
  html: '<span class="pulse-ring"></span><span class="pulse-ring delay"></span><span class="pulse-dot"></span>',
  iconSize: [44, 44],
  iconAnchor: [22, 22],
  popupAnchor: [0, -18],
})

// Built with DOM nodes (not an HTML string) so location text is never interpreted as markup.
function popupContent(location) {
  const box = document.createElement('div')
  const title = document.createElement('strong'); title.textContent = location.title
  const address = document.createElement('p'); address.textContent = location.address
  const link = document.createElement('a'); link.href = directionsUrl(location); link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = 'Get directions'
  box.append(title, address, link)
  return box
}

export default function DropoffMapModal({ locations, pledge, onClose }) {
  const dialogRef = useRef(null)
  const mapElement = useRef(null)
  const mapRef = useRef(null)
  const markersRef = useRef({})
  const [activeId, setActiveId] = useState(null)

  useEffect(() => {
    dialogRef.current.showModal()
    const map = L.map(mapElement.current, { scrollWheelZoom: true })
    mapRef.current = map
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)
    locations.forEach(location => {
      markersRef.current[location.id] = L.marker([location.lat, location.lng], { icon: pulseIcon(false), title: location.title, keyboard: false })
        .bindPopup(popupContent(location))
        .on('click', () => focusLocation(location.id))
        .on('popupclose', () => setActiveId(current => current === location.id ? null : current))
        .addTo(map)
    })
    showAll()
    // The dialog is laid out after showModal(), so Leaflet needs to re-measure its container.
    const frame = requestAnimationFrame(() => { map.invalidateSize(); showAll() })
    return () => { cancelAnimationFrame(frame); map.remove(); markersRef.current = {} }
  }, [])

  useEffect(() => {
    Object.entries(markersRef.current).forEach(([id, marker]) => marker.setIcon(pulseIcon(id === activeId)))
  }, [activeId])

  function showAll() {
    const map = mapRef.current
    if (!map) return
    map.closePopup()
    setActiveId(null)
    map.fitBounds(L.latLngBounds(locations.map(location => [location.lat, location.lng])), { padding: [60, 60], maxZoom: 16 })
  }

  function focusLocation(id) {
    const location = locations.find(entry => entry.id === id)
    const map = mapRef.current
    if (!location || !map) return
    setActiveId(id)
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    map.flyTo([location.lat, location.lng], 17, { animate: !reduceMotion, duration: 1.1 })
    if (reduceMotion) markersRef.current[id]?.openPopup()
    else map.once('moveend', () => markersRef.current[id]?.openPopup())
  }

  return <dialog className="map-modal" ref={dialogRef} aria-labelledby="map-modal-title" onClose={onClose} onClick={event => { if (event.target === dialogRef.current) dialogRef.current.close() }}>
    <header className="map-modal-header">
      <div>
        <p className="eyebrow">Drop-off locations</p>
        <h2 id="map-modal-title">Where to drop off your items</h2>
        {pledge && <p className="map-modal-pledge">Thank you! Your pledge of <strong>{pledge}</strong> is recorded. Choose a location to see where to bring it.</p>}
      </div>
      <button className="small-button" type="button" onClick={() => dialogRef.current.close()} aria-label="Close drop-off map">Close</button>
    </header>
    <div className="map-modal-body">
      <ul className="map-locations">
        {locations.map(location => <li key={location.id}>
          <button type="button" className={location.id === activeId ? 'location-button active' : 'location-button'} aria-pressed={location.id === activeId} onClick={() => focusLocation(location.id)}>
            <strong>{location.title}</strong><span>{location.address}</span>
          </button>
        </li>)}
        <li><button type="button" className="small-button" onClick={showAll}>Show all locations</button></li>
      </ul>
      <div className="map-canvas" ref={mapElement} role="region" aria-label="Map of drop-off locations. Drag to move, scroll or pinch to zoom." />
    </div>
  </dialog>
}
