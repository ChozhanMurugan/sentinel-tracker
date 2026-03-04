// ============================================================
//  UI MODULE — sidebar, detail panel, stats, search, alerts
// ============================================================

const $ = id => document.getElementById(id);

// ── Detail panel ─────────────────────────────────────────────

export function showDetailPanel(data) {
    const panel = $('detail-panel');
    panel.classList.add('open');

    if (data.type === 'ship') {
        $('detail-title').textContent = data.name || 'Unknown Vessel';
        $('detail-sub').textContent = `MMSI: ${data.mmsi}`;
        $('detail-badge').textContent = '🚢 SHIP';
        $('detail-badge').className = 'badge badge-ship';
        $('detail-body').innerHTML = `
      <div class="stat-row"><span>Speed</span><strong>${data.speed != null ? data.speed + ' kts' : 'N/A'}</strong></div>
      <div class="stat-row"><span>Heading</span><strong>${Math.round(data.heading)}°</strong></div>
      <div class="stat-row"><span>Nav Status</span><strong>${navStatus(data.status)}</strong></div>
      <div class="stat-row"><span>Last Update</span><strong>${timeAgo(data.lastUpdate)}</strong></div>`;
    } else {
        const mil = data.military;
        $('detail-title').textContent = data.callsign || data.icao24 || '—';
        $('detail-sub').textContent = `ICAO: ${data.icao24}  ·  ${data.country}`;
        $('detail-badge').textContent = mil ? '⭐ MILITARY' : '✈ COMMERCIAL';
        $('detail-badge').className = `badge ${mil ? 'badge-military' : 'badge-commercial'}`;
        $('detail-body').innerHTML = `
      <div class="stat-row"><span>Altitude</span><strong>${data.altitude != null ? data.altitude.toLocaleString() + ' m' : 'Ground'}</strong></div>
      <div class="stat-row"><span>Speed</span><strong>${data.speed != null ? data.speed + ' kts' : 'N/A'}</strong></div>
      <div class="stat-row"><span>Heading</span><strong>${data.heading}°</strong></div>
      <div class="stat-row"><span>Vert. Rate</span><strong>${data.vertRate != null ? data.vertRate + ' m/s' : 'N/A'}</strong></div>
      <div class="stat-row"><span>Squawk</span><strong>${data.squawk || 'N/A'}</strong></div>
      <div class="stat-row"><span>Origin</span><strong>${data.country}</strong></div>
      <div class="stat-row"><span>On Ground</span><strong>${data.onGround ? 'Yes' : 'No'}</strong></div>
      <div class="stat-row"><span>Last Update</span><strong>${timeAgo(data.lastUpdate)}</strong></div>`;
    }
}

export function hideDetailPanel() {
    $('detail-panel').classList.remove('open');
}

// ── Stats counters ────────────────────────────────────────────

export function updateStats({ commercial, military, ships, total }) {
    $('count-commercial').textContent = commercial.toLocaleString();
    $('count-military').textContent = military.toLocaleString();
    $('count-ships').textContent = ships.toLocaleString();
    $('count-total').textContent = total.toLocaleString();
}

// ── Alert feed ────────────────────────────────────────────────

export function pushAlert(text, level = 'info') {
    const feed = $('alert-feed');
    const item = document.createElement('div');
    item.className = `alert-item alert-${level}`;
    const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    item.innerHTML = `<span class="alert-time">${t}</span> ${text}`;
    feed.prepend(item);
    // cap at 30 items
    while (feed.children.length > 30) feed.removeChild(feed.lastChild);
}

// ── AIS status indicator ──────────────────────────────────────

export function setAISStatus(status) {
    const dot = $('ais-status-dot');
    const lbl = $('ais-status-lbl');
    const map = {
        'connecting': ['#ffd700', 'Connecting…'],
        'connected': ['#00ff88', 'Live'],
        'disconnected': ['#888', 'Disconnected'],
        'error': ['#ff3b3b', 'Error'],
        'no-key': ['#ff9900', 'No API Key'],
    };
    const [color, label] = map[status] || ['#888', status];
    if (dot) { dot.style.background = color; dot.style.boxShadow = `0 0 6px ${color}`; }
    if (lbl) lbl.textContent = label;
}

// ── OpenSky status indicator ──────────────────────────────────

export function setFlightStatus(ok) {
    const dot = $('sky-status-dot');
    const lbl = $('sky-status-lbl');
    if (dot) { dot.style.background = ok ? '#00ff88' : '#ff3b3b'; }
    if (lbl) lbl.textContent = ok ? 'Live' : 'Error';
}

// ── Last-refresh timestamp ────────────────────────────────────

export function setLastRefresh() {
    const el = $('last-refresh');
    if (el) el.textContent = new Date().toLocaleTimeString();
}

// ── Search filter (returns predicate) ────────────────────────

export function getSearchFilter() {
    const q = ($('search-box')?.value || '').trim().toUpperCase();
    if (!q) return () => true;
    return (d) => {
        const cs = (d.callsign || d.name || '').toUpperCase();
        const id = (d.icao24 || d.mmsi || '').toUpperCase();
        const cty = (d.country || '').toUpperCase();
        return cs.includes(q) || id.includes(q) || cty.includes(q);
    };
}

// ── Helpers ───────────────────────────────────────────────────

function timeAgo(ts) {
    const s = Math.round((Date.now() - ts) / 1000);
    if (s < 5) return 'just now';
    if (s < 60) return `${s}s ago`;
    return `${Math.round(s / 60)}m ago`;
}

function navStatus(code) {
    const s = ['Underway (engine)', 'At anchor', 'Not under command',
        'Restricted manoeuvring', 'Constrained by draught', 'Moored',
        'Aground', 'Engaged fishing', 'Underway (sailing)'];
    return s[code] || 'Unknown';
}
