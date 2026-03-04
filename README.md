# SENTINEL — Global Flight, Ship & Military Aircraft Tracker

A **Palantir-style** open-source real-time tracking dashboard.  
**100% Free** — no paid APIs, no server, no credit card required.

![Dark map UI with aircraft markers and sidebar](preview.png)

---

## ✈ Features

- **Commercial flight tracking** — live via [OpenSky Network](https://opensky-network.org) (free, no signup)
- **Military aircraft detection** — heuristic filtering on known ICAO hex blocks (US DoD, UK RAF, Russian AF, etc.) and callsign patterns (RCH, DUKE, SPAR, FORTE…)
- **Maritime vessel tracking** — live AIS via [aisstream.io](https://aisstream.io) WebSocket (free signup, no credit card)
- Dark military-ops UI — glassmorphism panels, animated icons, trail polylines
- Layer toggles, live statistics, search/filter, detail panel with full aircraft data
- Auto-refreshes every 20 seconds

---

## 🚀 Running Locally

The app uses ES modules so you need a simple HTTP server (due to browser CORS rules on `file://`).

### Option A — VS Code Live Server (easiest)
1. Install the **Live Server** extension in VS Code
2. Open the `tracker/` folder in VS Code
3. Right-click `index.html` → **Open with Live Server**

### Option B — Python (if installed)
```bash
cd tracker
python -m http.server 8787
# then open http://localhost:8787
```

### Option C — Node.js
```bash
npx serve tracker -p 8787
# then open http://localhost:8787
```

---

## 🔑 Ship Tracking Setup (Optional)

1. Sign up free at **https://aisstream.io** (no credit card)
2. Copy your API key
3. Click the **⚙ Settings** button in the top-right of the app
4. Paste your key and click **Save & Connect**
5. The AIS status indicator will turn green — ships appear on the map!

Your key is saved to `localStorage` so you only need to do this once per browser.

---

## 📡 Data Sources (All Free)

| Source | Data | Cost |
|---|---|---|
| [OpenSky Network](https://opensky-network.org) | Live ADS-B flights + military | Free |
| [aisstream.io](https://aisstream.io) | Live AIS ship positions | Free (signup) |
| [CartoDB](https://carto.com) | Dark map tiles | Free |
| [Leaflet.js](https://leafletjs.com) | Map library | Free, MIT license |

> **OpenSky anonymous limit**: ~100 requests/day. Register a free account for 4000/day.

---

## 🛡 Military Detection

Military classification uses two heuristics:
1. **ICAO-24 hex prefix** — matched against known blocks:
   - `AE0-AEF` → US Department of Defense
   - `43C` → UK Royal Air Force
   - `3A0-3A7` → French Air & Space Force
   - `781-783` → Russian military
   - `710` → Chinese PLAAF
   - …and more (see `js/config.js`)
2. **Callsign prefix** — e.g., `RCH` (Air Mobility Command), `DUKE`, `SPAR`, `FORTE`, `REACH`

> Note: Aircraft squawking civilian codes won't be detected. This is a best-effort heuristic, not authoritative intelligence.

---

## 📁 Project Structure

```
tracker/
├── index.html          ← Main HTML shell
├── styles/
│   └── main.css        ← Dark military-ops UI
└── js/
    ├── config.js       ← Settings, military ICAO sets
    ├── api.js          ← OpenSky fetch + aisstream WebSocket
    ← map.js          ← Leaflet map, markers, trails
    ├── ui.js           ← Stats, detail panel, search, alerts
    └── app.js          ← Orchestrator, polling loop, event wiring
```

---

## ⚠️ Disclaimer

This tool uses only publicly broadcast ADS-B and AIS signals — the same data every aircraft and ship voluntarily transmits. It does not intercept private communications or access classified systems.
