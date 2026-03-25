/**
 * SENTINEL \u2014 API Module
 * Connects to the backend WebSocket (ws://localhost:8000/ws).
 * Falls back to direct OpenSky polling if the backend is unavailable.
 */

import CONFIG from './config.js';

// \u2500\u2500 Backend WebSocket client \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

let _ws = null;
let _reconnectTimer = null;
let _reconnectDelay = 2000;    // doubles on each failure, max 30s
let _useBackend = true;    // set false if backend unavailable
let _onUpdate = null;    // callback(type, data)
let _onStats = null;    // callback(stats)

/**
 * Connect to the SENTINEL backend WebSocket.
 * @param {function} onUpdate  - called with (type, data) on snapshot/delta
 * @param {function} onStats   - called with stats object every 30s
 */
export function connectBackend(onUpdate, onStats) {
    _onUpdate = onUpdate;
    _onStats = onStats;
    _connectBackend();
}

function _connectBackend() {
    if (_ws) {
        try { _ws.close(); } catch (_) { }
    }

    const url = CONFIG.backendWs || 'ws://localhost:8000/ws';
    console.info('[API] Connecting to backend WS:', url);

    _ws = new WebSocket(url);

    _ws.onopen = () => {
        console.info('[API] Backend WS connected');
        _reconnectDelay = 2000;
        _useBackend = true;
    };

    _ws.onmessage = (ev) => {
        try {
            const msg = JSON.parse(ev.data);
            if (msg.type === 'snapshot' || msg.type === 'delta') {
                _onUpdate?.(msg.type, msg);
            } else if (msg.type === 'stats') {
                _onStats?.(msg);
            }
        } catch (err) {
            console.warn('[API] WS parse error:', err);
        }
    };

    _ws.onerror = () => {
        console.warn('[API] WS error \u2014 falling back to direct API');
    };

    _ws.onclose = () => {
        clearTimeout(_reconnectTimer);
        _reconnectTimer = setTimeout(() => {
            _connectBackend();
            _reconnectDelay = Math.min(_reconnectDelay * 2, 30000);
        }, _reconnectDelay);
    };
}

// \u2500\u2500 fetchFlights \u2014 direct OpenSky polling (no backend needed) \u2500\u2500\u2500\u2500\u2500

export async function fetchFlights() {
    try {
        const resp = await fetch(CONFIG.openskyUrl);
        if (!resp.ok) return [];
        const data = await resp.json();
        const states = data.states || [];
        return states
            .filter(s => s[6] != null && s[5] != null)
            .map(s => ({
                icao24: s[0],
                callsign: (s[1] || '').trim(),
                country: s[2] || '',
                lat: s[6],
                lon: s[5],
                altitude: s[7],
                speed: s[9],
                heading: s[10],
                vertRate: s[11],
                onGround: !!s[8],
                squawk: s[14] || '',
                military: _isMilitary(s[0], (s[1] || '').trim()),
                lastUpdate: (s[3] || Date.now() / 1000) * 1000,
                type: 'aircraft',
            }));
    } catch (e) {
        console.warn('[API] OpenSky poll error:', e);
        return [];
    }
}

// Quick heuristic \u2014 matches CONFIG.militaryIcaoRanges + callsign patterns
function _isMilitary(icao, cs) {
    try {
        const val = parseInt(icao, 16);
        const ranges = CONFIG.militaryIcaoRanges || [];
        for (const [lo, hi] of ranges) {
            if (val >= lo && val <= hi) return true;
        }
    } catch (_) {}
    const patterns = CONFIG.militaryCallsigns || [];
    for (const p of patterns) {
        if (cs.startsWith(p)) return true;
    }
    return false;
}

// \u2500\u2500 AIS ship tracking (aisstream.io WebSocket) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

let _aisWs = null;

export function connectAIS(key, onShip, onStatus) {
    if (!key) { onStatus?.('no-key'); return; }

    try {
        _aisWs = new WebSocket('wss://stream.aisstream.io/v0/stream');
    } catch (e) {
        onStatus?.('error');
        return;
    }

    _aisWs.onopen = () => {
        _aisWs.send(JSON.stringify({
            APIKey: key,
            BoundingBoxes: [[[-90, -180], [90, 180]]],
        }));
        onStatus?.('connected');
    };

    _aisWs.onmessage = (ev) => {
        try {
            const msg = JSON.parse(ev.data);
            const pos = msg?.Message?.PositionReport;
            if (!pos) return;
            const meta = msg.MetaData || {};
            onShip({
                mmsi: String(meta.MMSI || ''),
                name: (meta.ShipName || '').trim(),
                lat: pos.Latitude,
                lon: pos.Longitude,
                speed: pos.Sog,
                heading: pos.TrueHeading === 511 ? pos.Cog : pos.TrueHeading,
                country: meta.country || '',
                type: 'ship',
                lastUpdate: Date.now(),
            });
        } catch (_) {}
    };

    _aisWs.onerror = () => onStatus?.('error');
    _aisWs.onclose = () => onStatus?.('disconnected');
}

export function disconnectAIS() {
    if (_aisWs) {
        try { _aisWs.close(); } catch (_) {}
        _aisWs = null;
    }
}
