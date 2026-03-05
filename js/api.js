/**
 * SENTINEL — API Module
 * Connects to the backend WebSocket (ws://localhost:8000/ws).
 * Falls back to direct OpenSky polling if the backend is unavailable.
 */

import { CONFIG } from './config.js';

// ── Backend WebSocket client ──────────────────────────────────────

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
    _connect();
}

function _connect() {
    if (_ws) {
        try { _ws.close(); } catch (_) { }
    }

    const url = CONFIG.backendWs || 'ws://localhost:8000/ws';
    console.info('[API] Connecting to backend WS:', url);
    _setStatus('backend', 'connecting');

    _ws = new WebSocket(url);

    _ws.onopen = () => {
        console.info('[API] Backend WS connected ✓');
        _reconnectDelay = 2000;
        _useBackend = true;
        _setStatus('backend', 'live');
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
        console.warn('[API] WS error — falling back to direct API');
        _setStatus('backend', 'error');
    };

    _ws.onclose = () => {
        _setStatus('backend', 'disconnected');
        _scheduleReconnect();
    };
}

function _scheduleReconnect() {
    clearTimeout(_reconnectTimer);
    _reconnectTimer = setTimeout(() => {
        console.info('[API] Reconnecting in %dms …', _reconnectDelay);
        _connect();
        _reconnectDelay = Math.min(_reconnectDelay * 2, 30000);
    }, _reconnectDelay);
}

/** Send a heartbeat ping to keep the WS alive. */
export function pingBackend() {
    if (_ws?.readyState === WebSocket.OPEN) {
        _ws.send('ping');
    }
}

// ── REST helpers ──────────────────────────────────────────────────

const _base = () => CONFIG.backendApi || 'http://localhost:8000';

export async function fetchAircraftHistory(icao24, hours = 2) {
    const res = await fetch(`${_base()}/api/aircraft/${icao24}/history?hours=${hours}`);
    if (!res.ok) throw new Error(`History fetch failed: ${res.status}`);
    return res.json();
}

export async function fetchBbox(minlat, maxlat, minlon, maxlon) {
    const url = `${_base()}/api/aircraft/bbox/search?minlat=${minlat}&maxlat=${maxlat}&minlon=${minlon}&maxlon=${maxlon}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Bbox fetch failed: ${res.status}`);
    return res.json();
}

export async function fetchStats() {
    const res = await fetch(`${_base()}/api/stats`);
    if (!res.ok) throw new Error(`Stats fetch failed: ${res.status}`);
    return res.json();
}

// ── Fallback: Direct OpenSky polling (if backend unreachable) ─────

let _pollTimer = null;
let _pollCallback = null;

export function startDirectPoll(onData) {
    _pollCallback = onData;
    _doPoll();
}

export function stopDirectPoll() {
    clearTimeout(_pollTimer);
}

async function _doPoll() {
    try {
        const resp = await fetch(CONFIG.openSkyUrl);
        if (resp.ok) {
            const data = await resp.json();
            _pollCallback?.(data);
        }
    } catch (_) { }
    _pollTimer = setTimeout(_doPoll, (CONFIG.flightRefreshMs || 10000));
}

// ── Status pill helper ────────────────────────────────────────────

function _setStatus(source, state) {
    const pill = document.getElementById(
        source === 'backend' ? 'backendStatus' : 'openSkyStatus'
    );
    if (!pill) return;
    const labels = { live: 'Live', connecting: 'Connecting…', error: 'Error', disconnected: 'Offline' };
    const colors = { live: '#00ff88', connecting: '#ffd700', error: '#ff3b3b', disconnected: '#888' };
    pill.textContent = labels[state] || state;
    pill.style.color = colors[state] || '#fff';
}
