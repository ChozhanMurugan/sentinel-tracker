// ============================================================
//  MAP MODULE — Deck.gl WebGL Layer Manager
// ============================================================
import CONFIG from './config.js';

let deckgl;
let dataMap = new Map();
let vis = { commercial: true, military: true, ships: true };
let currentFilter = null;
let _onClick = null;

// ── Init ──────────────────────────────────────────────────────

export function initMap(onMarkerClick) {
    _onClick = onMarkerClick;
    
    deckgl = new deck.DeckGL({
        container: 'map',
        mapStyle: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
        initialViewState: {
            longitude: CONFIG.mapCenter[1],
            latitude: CONFIG.mapCenter[0],
            zoom: CONFIG.mapZoom,
            pitch: 45,
            bearing: 0
        },
        controller: true,
        layers: [],
        getTooltip: ({object}) => object && `${object.callsign || object.icao24 || object.name || 'Unknown'}`
    });

    return deckgl;
}

export function getMap() { return deckgl; }

// ── Entity management ─────────────────────────────────────────

export function upsertAircraft(ac) {
    if (ac.lat == null || ac.lon == null) return;
    dataMap.set(ac.icao24 || ac.callsign, {
        id: ac.icao24 || ac.callsign,
        type: 'aircraft',
        military: ac.military,
        lat: ac.lat,
        lon: ac.lon,
        heading: ac.heading || 0,
        ...ac,
    });
    scheduleRender();
}

export function upsertShip(ship) {
    if (ship.lat == null || ship.lon == null) return;
    dataMap.set('ship_' + (ship.mmsi || ship.name), {
        id: 'ship_' + (ship.mmsi || ship.name),
        type: 'ship',
        ...ship,
    });
    scheduleRender();
}

export function pruneStaleMarkers(maxAgeMs = 90000) {
    const now = Date.now();
    let changed = false;
    for (const [id, e] of dataMap) {
        if (now - (e.lastUpdate || e.ts * 1000 || now) > maxAgeMs) {
            dataMap.delete(id);
            changed = true;
        }
    }
    if (changed) scheduleRender();
}

// ── Layer visibility & rendering ──────────────────────────────

export function setLayerVisible(type, visible) {
    vis[type] = !!visible;
    scheduleRender();
}

export function setMapFilter(predicateFn) {
    currentFilter = predicateFn;
    scheduleRender();
}

let _raf = null;
function scheduleRender() {
    if (_raf) return;
    _raf = requestAnimationFrame(() => {
        _raf = null;
        renderLayers();
    });
}

function renderLayers() {
    if (!deckgl) return;
    
    let planes = [];
    let ships = [];
    
    for (const e of dataMap.values()) {
        if (currentFilter && !currentFilter(e)) continue;
        
        if (e.type === 'ship' && vis.ships) ships.push(e);
        else if (e.type === 'aircraft') {
            if (e.military && vis.military) planes.push(e);
            else if (!e.military && vis.commercial) planes.push(e);
        }
    }

    const shipLayer = new deck.ScatterplotLayer({
        id: 'ships-layer',
        data: ships,
        pickable: true,
        opacity: 0.8,
        stroked: true,
        filled: true,
        radiusScale: 1,
        radiusMinPixels: 3,
        radiusMaxPixels: 10,
        lineWidthMinPixels: 1,
        getPosition: d => [d.lon, d.lat],
        getFillColor: d => [255, 215, 0, 200],
        getLineColor: d => [255, 255, 255],
        onClick: info => { if (info.object) _onClick(info.object); }
    });

    const planeLayer = new deck.ScatterplotLayer({
        id: 'planes-layer',
        data: planes,
        pickable: true,
        opacity: 0.8,
        stroked: true,
        filled: true,
        radiusScale: 1,
        radiusMinPixels: 4,
        radiusMaxPixels: 15,
        lineWidthMinPixels: 1,
        getPosition: d => [d.lon, d.lat],
        getFillColor: d => d.anomaly ? [255, 165, 0, 255] : (d.military ? [255, 59, 59, 220] : [0, 212, 255, 200]),
        getLineColor: d => d.anomaly ? [255, 255, 255, 255] : [0, 0, 0, 100],
        onClick: info => { if (info.object) _onClick(info.object); }
    });

    deckgl.setProps({ layers: [shipLayer, planeLayer] });
}

// ── Stats ─────────────────────────────────────────────────────

export function getMarkerCounts() {
    let c = 0, m = 0, s = 0;
    for (const e of dataMap.values()) {
        if (e.type === 'ship') s++;
        else if (e.military) m++;
        else c++;
    }
    return { commercial: c, military: m, ships: s, total: dataMap.size };
}
