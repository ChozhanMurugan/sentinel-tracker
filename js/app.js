// ============================================================
//  APP.JS — Orchestrator
// ============================================================
import CONFIG from './config.js';
import { fetchFlights, connectAIS, disconnectAIS } from './api.js';
import {
    initMap, getMap, upsertAircraft, upsertShip,
    pruneStaleMarkers, setLayerVisible, setMapFilter,
    getMarkerCounts
} from './map.js';
import {
    showDetailPanel, hideDetailPanel, updateStats, pushAlert,
    setAISStatus, setFlightStatus, setLastRefresh,
    getSearchFilter
} from './ui.js';
import { CommandProcessor } from './commands.js';

// ── State ─────────────────────────────────────────────────────
const layers = { commercial: true, military: true, ships: true };
let aisstreamKey = localStorage.getItem('aisstreamKey') || CONFIG.aisstreamKey || '';
let cmd;

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
    });

    wireControls();
    tick();
    setInterval(tick, CONFIG.flightRefreshMs);
    startAIS();

    pushAlert('SENTINEL online — feeds initialising…', 'info');
    pushAlert('Type commands below  ·  try "help"', 'info');
});

// ── Polling ───────────────────────────────────────────────────
async function tick() {
    try {
        const flights = await fetchFlights();
        const filter = getSearchFilter();

        for (const ac of flights) {
            upsertAircraft(ac);
        }

        pruneStaleMarkers(90000);

        // Apply search filter to canvas layer in one shot
        setMapFilter(filter === null ? null : (e) => {
            if (e.type === 'ship') return filter(e);
            return filter(e);
        });

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
            if (status === 'error') pushAlert('AIS error — retrying in 30s', 'warn');
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
            pushAlert('AIS key saved. Connecting…', 'success');
        }
    });

    // Sidebar toggle
    document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
        const s = document.getElementById('sidebar');
        const t = document.getElementById('sidebar-toggle');
        s.classList.toggle('collapsed');
        t.textContent = s.classList.contains('collapsed') ? '▶' : '◀';
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

    // Click on map closes detail panel
    getMap()?.on('click', () => {
        // Small delay — canvas-layer click fires first
        setTimeout(() => {
            if (!document.getElementById('detail-panel')._justOpened) {
                hideDetailPanel();
            }
        }, 50);
    });
}

// ── Marker click ──────────────────────────────────────────────
function onMarkerClick(data) {
    showDetailPanel(data);
    const panel = document.getElementById('detail-panel');
    if (panel) { panel._justOpened = true; setTimeout(() => { panel._justOpened = false; }, 100); }
}
