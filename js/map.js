// ============================================================
//  MAP MODULE — thin wrapper around CanvasLayer + Leaflet map
// ============================================================
import CONFIG from './config.js';
import { CanvasLayer } from './canvas-layer.js';

let map;
let canvasLayer;

// ── Init ──────────────────────────────────────────────────────

export function initMap(onMarkerClick) {
    map = L.map('map', {
        center: CONFIG.mapCenter,
        zoom: CONFIG.mapZoom,
        zoomControl: false,
        preferCanvas: true,
    });

    L.tileLayer(CONFIG.tileUrl, {
        attribution: CONFIG.tileAttribution,
        maxZoom: 19,
        subdomains: 'abcd',
    }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    canvasLayer = new CanvasLayer(map, onMarkerClick);

    return map;
}

export function getMap() { return map; }

// ── Entity management ─────────────────────────────────────────

export function upsertAircraft(ac) {
    if (ac.lat == null || ac.lon == null) return;
    canvasLayer.upsert({
        id: ac.icao24 || ac.callsign,
        type: 'aircraft',
        military: ac.military,
        lat: ac.lat,
        lon: ac.lon,
        heading: ac.heading || 0,
        ...ac,
    });
}

export function upsertShip(ship) {
    if (ship.lat == null || ship.lon == null) return;
    canvasLayer.upsert({
        id: 'ship_' + (ship.mmsi || ship.name),
        type: 'ship',
        ...ship,
    });
}

export function pruneStaleMarkers(maxAgeMs = 90000) {
    canvasLayer.prune(maxAgeMs);
}

// ── Layer visibility ──────────────────────────────────────────

export function setLayerVisible(type, visible) {
    // type: 'commercial' | 'military' | 'ships'
    canvasLayer.setVisible(type, visible);
}

// ── Search filter ─────────────────────────────────────────────

export function setMapFilter(predicateFn) {
    canvasLayer.setFilter(predicateFn);
}

// ── Stats ─────────────────────────────────────────────────────

export function getMarkerCounts() {
    return canvasLayer.getCounts();
}
