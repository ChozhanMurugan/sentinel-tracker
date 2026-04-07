// ============================================================
//  APP.JS — Orchestrator
// ============================================================
import CONFIG from './config.js?v=3';
import { fetchFlights, connectAIS, disconnectAIS } from './api.js?v=3';
import {
    initMap, getMap, upsertAircraft, upsertShip,
    pruneStaleMarkers, setLayerVisible, setMapFilter,
    getMarkerCounts
} from './map.js?v=3';
import {
    showDetailPanel, hideDetailPanel, updateStats, pushAlert,
    setAISStatus, setFlightStatus, setLastRefresh,
    getSearchFilter
} from './ui.js?v=3';
import { CommandProcessor } from './commands.js?v=3';

// ── State ─────────────────────────────────────────────────────
const layers = { commercial: true, military: true, ships: true };
let aisstreamKey = localStorage.getItem('aisstreamKey') || CONFIG.aisstreamKey || '';
let cmd;

// ── Backend WebSocket ─────────────────────────────────────────
let _ws = null;
let _wsConnected = false;
let _wsReconnectTimer = null;
let _wsReconnectDelay = 2000;
const _WS_URL = `ws://${location.host}/ws`;  // proxied via nginx

// ── ML Intelligence ──────────────────────────────────────────
let _mlWs = null;
let _mlReconnectTimer = null;
let _mlReconnectDelay = 3000;
const _anomalyMap = new Map();   // icao24 -> anomaly data

// ── Startup ───────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    initMap(onMarkerClick);

    // Command processor
    cmd = new CommandProcessor({
        map: getMap(),
        toggleLayer: (name, on) => { layers[name] = on; setLayerVisible(name, on); },
        setSearch: applySearch,
        saveKey: saveAISKey,
        pushAlert,
        getAnomalies: () => _anomalyMap,
    });

    wireControls();
    startBackendWS();   // primary — backend WebSocket
    startAIS();
    startML();

    pushAlert('SENTINEL online \u2014 feeds initialising\u2026', 'info');
    pushAlert('Type commands below  \u00b7  try "help"', 'info');
});

// ── Backend WebSocket (primary data source) ───────────────────
/**
 * Maps compact backend field names → frontend field names expected
 * by upsertAircraft() / map.js
 */
function _normaliseAircraft(ac) {
    return {
        icao24:    ac.id   || ac.icao24,
        callsign:  ac.cs   || ac.callsign || '',
        country:   ac.cty  || ac.country  || '',
        lat:       ac.lat,
        lon:       ac.lon,
        altitude:  ac.alt  != null ? ac.alt  : ac.altitude,
        speed:     ac.spd  != null ? ac.spd  : ac.speed,
        heading:   ac.hdg  != null ? ac.hdg  : ac.heading,
        vertRate:  ac.vrt  != null ? ac.vrt  : ac.vertRate,
        onGround:  ac.gnd  != null ? ac.gnd  : ac.onGround,
        squawk:    ac.sq   || ac.squawk || '',
        military:  ac.mil  != null ? ac.mil  : (ac.military || false),
        lastUpdate:(ac.ts  ? ac.ts * 1000 : null) || ac.lastUpdate || Date.now(),
        type: 'aircraft',
    };
}

function _normaliseShip(s) {
    return {
        mmsi:      s.id  || s.mmsi,
        name:      s.cs  || s.name || '',
        country:   s.cty || s.country || '',
        lat:       s.lat,
        lon:       s.lon,
        speed:     s.spd != null ? s.spd : s.speed,
        heading:   s.hdg != null ? s.hdg : s.heading,
        lastUpdate:(s.ts  ? s.ts * 1000 : null) || s.lastUpdate || Date.now(),
        type: 'ship',
    };
}

function _applySnapshot(msg) {
    const aircraft = msg.aircraft || msg.upsert || [];
    const ships    = msg.ships    || [];
    for (const ac of aircraft) upsertAircraft(_normaliseAircraft(ac));
    for (const s  of ships)    upsertShip(_normaliseShip(s));
    pruneStaleMarkers(90000);
    updateStats(getMarkerCounts());
    setLastRefresh();
    setFlightStatus(true);
}

function _applyDelta(msg) {
    const upserts = msg.upsert || [];
    const removes = msg.remove || [];
    for (const ac of upserts) upsertAircraft(_normaliseAircraft(ac));
    // removed IDs — pruneStaleMarkers will clean them naturally
    pruneStaleMarkers(90000);
    updateStats(getMarkerCounts());
    setLastRefresh();
    setFlightStatus(true);
}

function startBackendWS() {
    if (_ws) { try { _ws.close(); } catch (_) {} }

    console.info('[WS] Connecting to', _WS_URL);
    try { _ws = new WebSocket(_WS_URL); }
    catch (e) {
        console.warn('[WS] Could not create WebSocket, falling back to polling');
        _startPollingFallback();
        return;
    }

    _ws.onopen = () => {
        _wsConnected = true;
        _wsReconnectDelay = 2000;
        console.info('[WS] Connected to backend');
        setFlightStatus(true);
    };

    _ws.onmessage = (ev) => {
        try {
            const msg = JSON.parse(ev.data);
            if (msg.type === 'snapshot') _applySnapshot(msg);
            else if (msg.type === 'delta') _applyDelta(msg);
        } catch (err) { console.warn('[WS] parse error', err); }
    };

    _ws.onerror = () => {
        console.warn('[WS] error');
        _wsConnected = false;
    };

    _ws.onclose = () => {
        _wsConnected = false;
        console.warn('[WS] closed — reconnecting in', _wsReconnectDelay, 'ms');
        clearTimeout(_wsReconnectTimer);
        _wsReconnectTimer = setTimeout(() => {
            _wsReconnectDelay = Math.min(_wsReconnectDelay * 2, 30000);
            startBackendWS();
        }, _wsReconnectDelay);
    };
}

// ── Polling fallback (used only if backend WS unavailable) ────
let _fallbackInterval = null;
function _startPollingFallback() {
    if (_fallbackInterval) return;
    pushAlert('Backend WS unavailable — using direct OpenSky poll', 'warn');
    _fallbackInterval = setInterval(tick, CONFIG.flightRefreshMs);
    tick();
}

async function tick() {
    try {
        const flights = await fetchFlights();
        for (const ac of flights) upsertAircraft(ac);
        pruneStaleMarkers(90000);
        updateStats(getMarkerCounts());
        setLastRefresh();
        setFlightStatus(true);
    } catch (e) {
        setFlightStatus(false);
        console.error('[App] tick:', e);
    }
}

// ── AIS ───────────────────────────────────────────────────────
function startAIS() {
    if (!aisstreamKey) { setAISStatus('no-key'); return; }

    connectAIS(
        aisstreamKey,
        (vessel) => {
            upsertShip(vessel);
            updateStats(getMarkerCounts());
        },
        (status) => {
            setAISStatus(status);
            if (status === 'connected') pushAlert('Ship AIS feed connected', 'success');
            if (status === 'error') pushAlert('AIS error \u2014 retrying in 30s', 'warn');
            if (status === 'disconnected') setTimeout(startAIS, 30000);
        },
    );
}

function saveAISKey(key) {
    aisstreamKey = key;
    localStorage.setItem('aisstreamKey', key);
    disconnectAIS();
    startAIS();
}

// ── Search ────────────────────────────────────────────────────
function applySearch(q) {
    const box = document.getElementById('search-box');
    if (box) box.value = q;

    const upper = q.trim().toUpperCase();
    if (!upper) {
        setMapFilter(null);
        return;
    }
    setMapFilter((e) => {
        const cs = (e.callsign || e.name || '').toUpperCase();
        const id = (e.icao24 || e.mmsi || '').toUpperCase();
        const cty = (e.country || '').toUpperCase();
        return cs.includes(upper) || id.includes(upper) || cty.includes(upper);
    });
}

// ── Controls ──────────────────────────────────────────────────
function wireControls() {
    // Layer toggles
    document.querySelectorAll('.layer-toggle').forEach(el => {
        el.addEventListener('change', () => {
            const layer = el.dataset.layer;
            layers[layer] = el.checked;
            setLayerVisible(layer, el.checked);
        });
    });

    // Detail panel close
    document.getElementById('detail-close')?.addEventListener('click', hideDetailPanel);

    // Search box
    document.getElementById('search-box')?.addEventListener('input', (e) => {
        applySearch(e.target.value);
    });

    // Settings modal
    document.getElementById('settings-btn')?.addEventListener('click', () => {
        document.getElementById('settings-modal').classList.toggle('open');
    });
    document.getElementById('settings-close')?.addEventListener('click', () => {
        document.getElementById('settings-modal').classList.remove('open');
    });
    document.getElementById('save-ais-key')?.addEventListener('click', () => {
        const key = document.getElementById('ais-key-input')?.value.trim();
        if (key) {
            saveAISKey(key);
            document.getElementById('settings-modal').classList.remove('open');
            pushAlert('AIS key saved. Connecting\u2026', 'success');
        }
    });

    // Sidebar toggle
    document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
        const s = document.getElementById('sidebar');
        const t = document.getElementById('sidebar-toggle');
        s.classList.toggle('collapsed');
        t.textContent = s.classList.contains('collapsed') ? '\u25b6' : '\u25c0';
    });

    // Command terminal
    const terminal = document.getElementById('terminal-input');
    terminal?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const val = terminal.value.trim();
            if (val) cmd.run(val);
            terminal.value = '';
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            terminal.value = cmd.histUp();
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            terminal.value = cmd.histDown();
        }
    });

    // Click on map background closes detail panel
    document.getElementById('map')?.addEventListener('click', () => {
        // Small delay to allow layer clicks to process first
        setTimeout(() => {
            const panel = document.getElementById('detail-panel');
            if (panel && !panel._justOpened) {
                hideDetailPanel();
            }
        }, 50);
    });
}

// ── Marker click ──────────────────────────────────────────────
function onMarkerClick(data) {
    // Enrich with ML data if available
    const mlData = _anomalyMap.get(data.icao24);
    if (mlData) {
        data.anomaly = true;
        data.anomalyScore = mlData.anomaly_score;
        data.anomalyReasons = mlData.reasons;
        data.milConfidence = mlData.mil_confidence;
        data.milMethod = mlData.mil_method;
        data.milLabel = mlData.mil_label;
    }
    showDetailPanel(data);
    const panel = document.getElementById('detail-panel');
    if (panel) { panel._justOpened = true; setTimeout(() => { panel._justOpened = false; }, 100); }
}

// ── ML Intelligence WebSocket ─────────────────────────────────
function startML() {
    if (!CONFIG.mlWs) return;

    const url = CONFIG.mlWs;
    console.info('[ML] Connecting to ML service:', url);

    try {
        _mlWs = new WebSocket(url);
    } catch (e) {
        console.warn('[ML] WebSocket creation failed:', e);
        _scheduleMLReconnect();
        return;
    }

    _mlWs.onopen = () => {
        console.info('[ML] Connected to ML service');
        _mlReconnectDelay = 3000;
        pushAlert('ML Intelligence connected', 'success');
    };

    _mlWs.onmessage = (ev) => {
        try {
            const msg = JSON.parse(ev.data);
            if (msg.type === 'anomalies' || msg.type === 'snapshot') {
                _handleMLAnomalies(msg.anomalies || []);
            }
        } catch (err) {
            console.warn('[ML] parse error:', err);
        }
    };

    _mlWs.onerror = () => {
        console.warn('[ML] WebSocket error');
    };

    _mlWs.onclose = () => {
        console.info('[ML] Disconnected');
        _scheduleMLReconnect();
    };
}

function _scheduleMLReconnect() {
    clearTimeout(_mlReconnectTimer);
    _mlReconnectTimer = setTimeout(() => {
        startML();
        _mlReconnectDelay = Math.min(_mlReconnectDelay * 2, 30000);
    }, _mlReconnectDelay);
}

function _handleMLAnomalies(anomalies) {
    _anomalyMap.clear();

    for (const a of anomalies) {
        _anomalyMap.set(a.icao24, a);
        // Flag entity in canvas layer
        upsertAircraft({
            ...a,
            anomaly: true,
            anomalyReasons: a.reasons,
            lastUpdate: Date.now(),
        });
    }

    if (anomalies.length > 0) {
        const top = anomalies[0];
        const reason = top.reasons?.[0] || 'unusual pattern';
        if (anomalies.length === 1) {
            pushAlert(`\u26a0 Anomaly: ${top.callsign || top.icao24} \u2014 ${reason}`, 'warn');
        } else {
            pushAlert(`\u26a0 ${anomalies.length} anomalies detected (e.g. ${top.callsign || top.icao24}: ${reason})`, 'warn');
        }
    }
}

// Export for commands
export function getAnomalyMap() { return _anomalyMap; }
