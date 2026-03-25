// ============================================================
//  TRACKER CONFIG — edit values here to customise behaviour
// ============================================================

const CONFIG = {
    // ── Map ────────────────────────────────────────────────────
    mapCenter: [30, 0],    // [lat, lng] — centred on Atlantic
    mapZoom: 3,
    tileUrl: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    tileAttribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',

    // ── Refresh ────────────────────────────────────────────────
    flightRefreshMs: 10000,   // 10 s — OpenSky minimum safe interval
    shipRefreshMs: 0,         // ships come in via live websocket (aisstream.io)

    // ── Backend (Phase 1) ──────────────────────────────────────
    // Set these to your backend URL once docker-compose is running
    backendWs: 'ws://localhost:8000/ws',   // WebSocket live stream
    backendApi: 'http://localhost:8000',     // REST API base

    // ── ML Intelligence (sentinel-ml) ───────────────────────────
    mlWs: 'ws://localhost:8001/ws',          // ML anomaly WebSocket
    mlApi: 'http://localhost:8001',           // ML REST API base

    // ── OpenSky Network (fallback) ──────────────────────────────
    openskyUrl: 'https://opensky-network.org/api/states/all',

    // ── aisstream.io ──────────────────────────────────────────
    // Get a FREE key at https://aisstream.io (no credit card)
    aisstreamWs: 'wss://stream.aisstream.io/v0/stream',
    aisstreamKey: '',   // ⚠️ DO NOT commit your key here. Use the ⚙ Settings button in the app or type: key YOUR_KEY in the terminal bar.

    // ── Military Classification ────────────────────────────────
    // Known military ICAO-24 hex prefix ranges (first 3 hex chars)
    militaryIcaoPrefixes: new Set([
        'ae0', 'ae1', 'ae2', 'ae3', 'ae4', 'ae5', 'ae6', 'ae7', 'ae8', 'ae9',  // US DoD block (AE0000-AE9FFF)
        'aea', 'aeb', 'aec', 'aed', 'aee', 'aef',
        '43c',  // UK RAF
        '3a0', '3a1', '3a2', '3a3', '3a4', '3a5', '3a6', '3a7',  // French Air & Space Force
        '3c4', '3c5', '3c6', '3c7', '3c8', '3c9',  // German Luftwaffe / Heer
        '781', '782', '783',  // Russian military
        '7800', '7801',      // Chinese PLA
        '710',              // Chinese PLAAF
        '500', '501',        // Canadian Armed Forces
        'c80', 'c81', 'c82',  // Australian RAAF
        '4b8', '4b9',        // Swiss Air Force
        '340', '341',        // Spanish Air Force
        '484', '485',        // Italian Air Force
        '4a0', '4a1',        // Belgian Air Component
        '460', '461',        // Dutch Air Force
        '440', '441',        // Norwegian Air Force
        '458', '459',        // Danish Air Force
        '478',              // Finnish Air Force
        // ―― Iran (IRIAF — Islamic Republic of Iran Air Force) ――
        '730', '731', '732', '733', '734', '735', '736', '737',  // ICAO block 730000-737FFF
        // ―― India (IAF — Indian Air Force) ――
        '800', '801', '802', '803', '804', '805', '806', '807',  // ICAO block 800000-83FFFF
        '808', '809', '80a', '80b', '80c', '80d', '80e', '80f',
        '810', '811', '812', '813', '814', '815', '816', '817',
        '818', '819', '81a', '81b', '81c', '81d', '81e', '81f',
        '820', '821', '822', '823', '824', '825', '826', '827',
        '828', '829', '82a', '82b', '82c', '82d', '82e', '82f',
        '830', '831', '832', '833', '834', '835', '836', '837',
        '838', '839', '83a', '83b', '83c', '83d', '83e', '83f',
    ]),

    // Callsign prefix patterns that strongly indicate military / government
    militaryCallsignPatterns: [
        /^RCH/,     // US Air Mobility Command (AMC)
        /^DUKE/,    // US Air Force
        /^SPAR/,    // US Air Force Special Airlift Mission
        /^FORTE/,   // USAF TACAMO survivable comms
        /^DOOM/,
        /^REACH/,
        /^TOPGUN/,
        /^NAVY/,
        /^ARMY/,
        /^USMC/,
        /^GOLD[0-9]/,
        /^DRAGON[0-9]/,
        /^HOOK/,
        /^VENUS/,
        /^DARKSTAR/,
        /^KNIGHT[0-9]/,
        /^VIPER[0-9]/,
        /^F-35/,
        /^B-52/,
        /^C-130/,
        // ―― Iran (IRIAF) ――
        /^IRI/,     // Islamic Republic of Iran (IRIAF transport / tanker callsigns)
        /^IRIAF/,
        /^IRAF/,
        /^YAS/,     // Iranian Armed Forces designator
        // ―― India (IAF) ――
        /^IAF/,     // Indian Air Force
        /^INDIA[0-9]/, // IAF ferry / special mission flights
        /^RNVS/,    // Research & Analysis Wing (RAW) special flights
        /^VIP[0-9]/, // Indian Government / VIP Air Transport Unit
    ],

    // ── UI ─────────────────────────────────────────────────────
    maxFlightMarkers: 8000,
    trailLength: 5,   // number of past positions to draw as trail
};

export default CONFIG;
