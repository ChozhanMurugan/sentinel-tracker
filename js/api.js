// ============================================================
//  API MODULE — OpenSky Network (flights) + aisstream.io (ships)
//  All sources are 100 % FREE, no credit card required.
// ============================================================
import CONFIG from './config.js';

// ── helpers ──────────────────────────────────────────────────

/**
 * Classify an aircraft as 'military' based on its ICAO-24 hex address
 * and callsign against known military blocks.
 * @param {string} icao24   e.g. "ae1234"
 * @param {string} callsign e.g. "RCH214"
 * @returns {boolean}
 */
export function isMilitary(icao24, callsign) {
    if (!icao24) return false;
    const hex3 = icao24.slice(0, 3).toLowerCase();
    if (CONFIG.militaryIcaoPrefixes.has(hex3)) return true;
    if (callsign) {
        const cs = callsign.trim().toUpperCase();
        for (const pat of CONFIG.militaryCallsignPatterns) {
            if (pat.test(cs)) return true;
        }
    }
    return false;
}

/**
 * Parse a raw OpenSky state vector array into a clean object.
 * State vector indices per OpenSky docs:
 * 0=icao24, 1=callsign, 2=origin_country, 3=time_position, 4=last_contact,
 * 5=longitude, 6=latitude, 7=baro_altitude, 8=on_ground, 9=velocity,
 * 10=true_track, 11=vertical_rate, 12=sensors, 13=geo_altitude,
 * 14=squawk, 15=spi, 16=position_source
 */
function parseState(s) {
    return {
        icao24: s[0] || '',
        callsign: (s[1] || '').trim() || s[0],
        country: s[2] || 'Unknown',
        lon: s[5],
        lat: s[6],
        altitude: s[7] != null ? Math.round(s[7]) : null,   // metres
        onGround: s[8] || false,
        speed: s[9] != null ? Math.round(s[9] * 1.94384) : null, // kts
        heading: s[10] != null ? Math.round(s[10]) : 0,
        vertRate: s[11] != null ? s[11].toFixed(1) : null,
        squawk: s[14] || '',
        military: isMilitary(s[0], s[1]),
        type: 'aircraft',
        lastUpdate: Date.now(),
    };
}

// ── OpenSky Network ───────────────────────────────────────────

/**
 * Fetch all live aircraft states from OpenSky Network (FREE, no key).
 * Returns an array of parsed state objects.
 */
export async function fetchFlights() {
    try {
        const res = await fetch(CONFIG.openskyUrl, {
            headers: { 'Accept': 'application/json' },
            cache: 'no-store',
        });
        if (!res.ok) throw new Error(`OpenSky ${res.status}: ${res.statusText}`);
        const data = await res.json();
        if (!data.states) return [];
        // Filter out aircraft without valid position or that are on the ground
        return data.states
            .filter(s => s[5] != null && s[6] != null)
            .map(parseState);
    } catch (err) {
        console.warn('[API] fetchFlights error:', err.message);
        return [];
    }
}

// ── aisstream.io WebSocket (ship AIS data) ────────────────────

let aisSock = null;
let aisActive = false;

/**
 * Connect to aisstream.io WebSocket for live ship AIS positions.
 * Calls onVessel(vessel) for every new position message.
 * Calls onStatus(msg) for connection status updates.
 *
 * @param {string}   apiKey    — free key from https://aisstream.io
 * @param {Function} onVessel  — callback(vesselObj)
 * @param {Function} onStatus  — callback(statusString)
 */
export function connectAIS(apiKey, onVessel, onStatus) {
    if (!apiKey) {
        onStatus?.('no-key');
        return;
    }
    if (aisSock) aisSock.close();

    onStatus?.('connecting');
    aisSock = new WebSocket(CONFIG.aisstreamWs);

    aisSock.onopen = () => {
        aisActive = true;
        onStatus?.('connected');
        aisSock.send(JSON.stringify({
            APIKey: apiKey,
            BoundingBoxes: [[[-90, -180], [90, 180]]],  // whole world
            FilterMessageTypes: ['PositionReport'],
        }));
    };

    aisSock.onmessage = (ev) => {
        try {
            const msg = JSON.parse(ev.data);
            if (msg.MessageType !== 'PositionReport') return;
            const p = msg.Message?.PositionReport;
            const m = msg.MetaData;
            if (!p || p.Latitude == null || p.Longitude == null) return;

            const vessel = {
                mmsi: String(m?.MMSI || p.UserID || ''),
                name: (m?.ShipName || 'Unknown').trim() || 'Unknown',
                lat: p.Latitude,
                lon: p.Longitude,
                heading: p.TrueHeading ?? p.Cog ?? 0,
                speed: p.Sog != null ? Math.round(p.Sog) : null,
                status: p.NavigationalStatus ?? 0,
                type: 'ship',
                lastUpdate: Date.now(),
            };
            onVessel(vessel);
        } catch (e) { /* ignore parse errors */ }
    };

    aisSock.onerror = () => { aisActive = false; onStatus?.('error'); };
    aisSock.onclose = () => { aisActive = false; onStatus?.('disconnected'); };
}

export function disconnectAIS() {
    aisSock?.close();
    aisSock = null;
    aisActive = false;
}

export function isAISConnected() { return aisActive; }
