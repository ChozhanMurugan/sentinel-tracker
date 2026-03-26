// ============================================================
//  COMMANDS — Semantic command processor for the terminal bar
//  Understands natural language instructions.
// ============================================================

const REGIONS = {
    'usa': { center: [39, -98], zoom: 5 },
    'us': { center: [39, -98], zoom: 5 },
    'america': { center: [39, -98], zoom: 5 },
    'united states': { center: [39, -98], zoom: 5 },
    'europe': { center: [51, 10], zoom: 5 },
    'eu': { center: [51, 10], zoom: 5 },
    'uk': { center: [54, -2], zoom: 6 },
    'england': { center: [54, -2], zoom: 6 },
    'iran': { center: [33, 53], zoom: 6 },
    'persia': { center: [33, 53], zoom: 6 },
    'india': { center: [22, 80], zoom: 5 },
    'russia': { center: [62, 95], zoom: 4 },
    'ukraine': { center: [49, 32], zoom: 6 },
    'china': { center: [36, 104], zoom: 5 },
    'middle east': { center: [26, 45], zoom: 5 },
    'middleeast': { center: [26, 45], zoom: 5 },
    'gulf': { center: [26, 52], zoom: 6 },
    'israel': { center: [31, 35], zoom: 7 },
    'turkey': { center: [39, 35], zoom: 6 },
    'germany': { center: [51, 10], zoom: 6 },
    'france': { center: [46, 2], zoom: 6 },
    'atlantic': { center: [30, -30], zoom: 4 },
    'pacific': { center: [20, -160], zoom: 4 },
    'asia': { center: [35, 105], zoom: 4 },
    'africa': { center: [0, 25], zoom: 4 },
    'australia': { center: [-25, 133], zoom: 5 },
    'korea': { center: [37, 127], zoom: 7 },
    'japan': { center: [36, 138], zoom: 6 },
    'world': { center: [30, 0], zoom: 3 },
    'global': { center: [30, 0], zoom: 3 },
    'reset': { center: [30, 0], zoom: 3 },
};

const HELP_TEXT =
    'Commands: show/hide [military|ships|commercial|all] \u00b7 ' +
    'zoom [region] \u00b7 search [text] \u00b7 clear \u00b7 key [ais-key] \u00b7 analyze \u00b7 status';

export class CommandProcessor {
    /**
     * @param {Object} ctx
     * @param {L.Map}   ctx.map
     * @param {Object}  ctx.toggleLayer   fn(name, on)
     * @param {fn}      ctx.setSearch     fn(query)
     * @param {fn}      ctx.saveKey       fn(key)
     * @param {fn}      ctx.pushAlert     fn(msg, level)
     */
    constructor(ctx) {
        this._map = ctx.map;
        this._toggleLayer = ctx.toggleLayer;
        this._setSearch = ctx.setSearch;
        this._saveKey = ctx.saveKey;
        this._push = ctx.pushAlert;
        this._getAnomalies = ctx.getAnomalies || (() => new Map());
        this._history = [];
        this._histIdx = -1;
    }

    run(raw) {
        raw = raw.trim();
        if (!raw) return;

        this._history.unshift(raw);
        this._histIdx = -1;

        const cmd = raw.toLowerCase().replace(/\s+/g, ' ');
        const result = this._dispatch(cmd, raw);
        this._push(`❯ ${raw}  →  ${result}`, 'info');
        return result;
    }

    histUp() { return this._nav(1); }
    histDown() { return this._nav(-1); }

    _nav(dir) {
        const next = this._histIdx + dir;
        if (next < 0) { this._histIdx = -1; return ''; }
        if (next >= this._history.length) return this._history[this._histIdx] || '';
        this._histIdx = next;
        return this._history[this._histIdx] || '';
    }

    // ── Dispatcher ───────────────────────────────────────────────

    _dispatch(cmd, raw) {
        // ── help ─────────────────────────────────────────────────
        if (/^(help|\?)$/.test(cmd)) return HELP_TEXT;

        // ── status ───────────────────────────────────────────────
        if (/^(status|info)$/.test(cmd)) return 'Tracker running. Type "help" for commands.';

        // ── analyze / anomalies ──────────────────────────────────
        if (/^(analyze|anomalies|ml|intelligence)$/.test(cmd)) return this._handleAnalyze();

        // ── show / hide / toggle ─────────────────────────────────
        const tv = cmd.match(/^(show|display|enable|turn on|unhide|hide|disable|turn off|toggle)\s+(all|commercial|flights?|military|ships?|vessels?)$/);
        if (tv) return this._handleVis(tv[1], tv[2]);

        // ── zoom / focus / fly / go ──────────────────────────────
        const zv = cmd.match(/^(zoom|focus|go to|fly to|center|pan to|jump to|show me)\s+(.+)$/);
        if (zv) return this._handleZoom(zv[2].trim());

        // ── search / filter / find ───────────────────────────────
        const sv = cmd.match(/^(search|filter|find|look for|show only|highlight)\s+(.+)$/i);
        if (sv) {
            const q = raw.replace(/^(search|filter|find|look for|show only|highlight)\s+/i, '');
            this._setSearch(q);
            return `Filtering: "${q}"`;
        }

        // ── clear / reset ────────────────────────────────────────
        if (/^(clear|reset( filter)?|show all|remove filter|no filter)$/.test(cmd)) {
            this._setSearch('');
            return 'Filter cleared — showing all contacts';
        }

        // ── AIS key ──────────────────────────────────────────────
        // "ais key abc123" / "set key abc123" / "key abc123" / "apikey abc123"
        const kv = cmd.match(/^(?:set |add |ais |aisstream )?(key|api[\s-]?key|token|aiskey|apikey)\s+(.+)$/);
        if (kv) {
            const key = raw.split(/\s+/).pop();
            this._saveKey(key);
            return `AIS key set. Connecting to ship feed…`;
        }
        // Also catch bare: "key <value>" where value is long string
        const bareKey = cmd.match(/^key\s+(\S{10,})$/);
        if (bareKey) {
            this._saveKey(raw.split(/\s+/).pop());
            return 'AIS key set. Connecting…';
        }

        // ── Loose region match (e.g. just typing "iran" or "europe") ─
        for (const [name, loc] of Object.entries(REGIONS)) {
            if (cmd === name || cmd.includes(name)) {
                this._flyTo(loc);
                return `Flying to ${_cap(name)}`;
            }
        }

        // ── Loose layer match (e.g. "military off") ──────────────
        for (const layer of ['military', 'ships', 'commercial', 'all', 'flights']) {
            if (cmd.includes(layer)) {
                const on = !cmd.includes('off') && !cmd.includes('hide') && !cmd.includes('disable');
                return this._handleVis(on ? 'show' : 'hide', layer);
            }
        }

        return `Unknown: "${raw}". Type "help"`;
    }

    _handleVis(verb, target) {
        const on = !['hide', 'disable', 'turn off'].includes(verb);
        const all = target === 'all';
        const toggle = (layer, v) => {
            const el = document.getElementById('toggle-' + layer);
            if (el) { el.checked = v; el.dispatchEvent(new Event('change')); }
        };
        if (all) {
            toggle('commercial', on); toggle('military', on); toggle('ships', on);
            return `${on ? 'Showing' : 'Hiding'} all layers`;
        }
        if (target.startsWith('ship') || target.startsWith('vessel')) {
            toggle('ships', on); return `Ships ${on ? 'visible' : 'hidden'}`;
        }
        if (target.startsWith('mil')) {
            toggle('military', on); return `Military ${on ? 'visible' : 'hidden'}`;
        }
        if (target === 'commercial' || target.startsWith('flight')) {
            toggle('commercial', on); return `Commercial ${on ? 'visible' : 'hidden'}`;
        }
        return `Unknown layer: ${target}`;
    }

    _handleZoom(target) {
        const t = target.toLowerCase();
        for (const [name, loc] of Object.entries(REGIONS)) {
            if (t === name || t.includes(name)) { this._flyTo(loc); return `Flying to ${_cap(name)}`; }
        }
        return `Unknown region: "${target}". Try: usa, europe, iran, india, russia, china, gulf…`;
    }

    _flyTo({ center, zoom }) {
        this._map.setProps({
            initialViewState: {
                longitude: center[1],
                latitude: center[0],
                zoom: zoom,
                pitch: 45,
                bearing: 0,
                transitionDuration: 1400
            }
        });
    }

    _handleAnalyze() {
        const anomalies = this._getAnomalies();
        if (!anomalies || anomalies.size === 0) {
            return 'No anomalies detected (ML service may still be training)';
        }
        const count = anomalies.size;
        const entries = [...anomalies.values()].slice(0, 5);
        const summaries = entries.map(a => {
            const id = a.callsign || a.icao24;
            const reason = (a.reasons || [])[0] || 'unusual';
            return `${id}: ${reason}`;
        });
        const more = count > 5 ? ` (+${count - 5} more)` : '';
        return `${count} anomalies: ${summaries.join(' | ')}${more}`;
    }
}

function _cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
