// ============================================================
//  CANVAS LAYER — renders ALL aircraft & ships on ONE <canvas>
//  Handles 10,000+ targets with zero DOM lag.
// ============================================================

export class CanvasLayer {
    constructor(map, onClick) {
        this._map = map;
        this._onClick = onClick;
        this._data = new Map();
        this._vis = { commercial: true, military: true, ships: true };
        this._filter = null;
        this._selected = null;
        this._hitBoxes = [];
        this._raf = null;
        this._pulse = 0;

        this._initCanvas();
        this._startPulse();
    }

    // ── Setup ─────────────────────────────────────────────────────

    _initCanvas() {
        const container = this._map.getContainer();

        this._canvas = document.createElement('canvas');
        const s = this._canvas.style;
        s.position = 'absolute';
        s.top = '0';
        s.left = '0';
        s.width = '100%';
        s.height = '100%';
        s.zIndex = '450';   // above tile panes (200-400), below sidebar (500+)
        s.pointerEvents = 'none';

        container.appendChild(this._canvas);
        this._ctx = this._canvas.getContext('2d');

        this._resize();

        this._map.on('move moveend zoom zoomend resize', () => {
            this._resize();
            this._scheduleDraw();
        });
        window.addEventListener('resize', () => this._resize());
        this._map.on('click', (e) => this._handleClick(e));
    }

    _resize() {
        const container = this._map.getContainer();
        const w = container.clientWidth || window.innerWidth;
        const h = container.clientHeight || window.innerHeight;
        if (this._canvas.width !== w || this._canvas.height !== h) {
            this._canvas.width = w;
            this._canvas.height = h;
        }
    }

    _startPulse() {
        let t = 0;
        const loop = () => {
            t += 0.045;
            this._pulse = (Math.sin(t) + 1) / 2;
            this._scheduleDraw();
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }

    // ── Public API ───────────────────────────────────────────────

    upsert(entity) { this._data.set(entity.id, entity); }

    prune(maxAgeMs) {
        const now = Date.now();
        for (const [id, e] of this._data) {
            if (now - e.lastUpdate > maxAgeMs) this._data.delete(id);
        }
    }

    setVisible(type, visible) { this._vis[type] = !!visible; this._scheduleDraw(); }
    setFilter(fn) { this._filter = fn; this._scheduleDraw(); }

    getCounts() {
        let c = 0, m = 0, s = 0;
        for (const e of this._data.values()) {
            if (e.type === 'ship') s++;
            else if (e.military) m++;
            else c++;
        }
        return { commercial: c, military: m, ships: s, total: this._data.size };
    }

    // ── Rendering ────────────────────────────────────────────────

    _scheduleDraw() {
        if (this._raf) return;
        this._raf = requestAnimationFrame(() => { this._raf = null; this._draw(); });
    }

    _draw() {
        const ctx = this._ctx;
        const map = this._map;
        const w = this._canvas.width;
        const h = this._canvas.height;

        ctx.clearRect(0, 0, w, h);
        this._hitBoxes = [];

        const PAD = 200; // px — cull only entities well past screen edge

        for (const [id, e] of this._data) {
            if (e.lat == null || e.lon == null) continue;

            const layer = e.type === 'ship' ? 'ships'
                : e.military ? 'military'
                    : 'commercial';

            if (!this._vis[layer]) continue;
            if (this._filter && !this._filter(e)) continue;

            const pt = map.latLngToContainerPoint(L.latLng(e.lat, e.lon));

            if (pt.x < -PAD || pt.x > w + PAD || pt.y < -PAD || pt.y > h + PAD) continue;

            const sel = (this._selected === id);

            if (e.type === 'ship') this._drawShip(ctx, pt.x, pt.y, e, sel);
            else this._drawPlane(ctx, pt.x, pt.y, e, sel);

            this._hitBoxes.push({ id, x: pt.x, y: pt.y, data: e });
        }
    }

    _drawPlane(ctx, x, y, e, sel) {
        const mil = e.military;
        const color = mil ? '#ff3b3b' : '#00d4ff';
        const sz = mil ? 9 : 7;
        const glow = sel ? 18 : 3 + this._pulse * (mil ? 9 : 5);
        const rad = (e.heading || 0) * Math.PI / 180;

        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(rad);
        ctx.shadowColor = color;
        ctx.shadowBlur = glow;

        ctx.beginPath();
        ctx.moveTo(0, -sz);
        ctx.lineTo(sz * 0.65, sz * 0.55);
        ctx.lineTo(0, sz * 0.2);
        ctx.lineTo(-sz * 0.65, sz * 0.55);
        ctx.closePath();

        ctx.fillStyle = sel ? '#ffffff' : color;
        ctx.fill();
        ctx.restore();
    }

    _drawShip(ctx, x, y, e, sel) {
        const color = '#ffd700';
        const sz = 5;
        const glow = sel ? 16 : 2 + this._pulse * 5;

        ctx.save();
        ctx.translate(x, y);
        ctx.shadowColor = color;
        ctx.shadowBlur = glow;

        ctx.beginPath();
        ctx.moveTo(0, -sz * 1.5);
        ctx.lineTo(sz, 0);
        ctx.lineTo(0, sz * 1.5);
        ctx.lineTo(-sz, 0);
        ctx.closePath();

        ctx.fillStyle = sel ? '#ffffff' : color;
        ctx.fill();
        ctx.restore();
    }

    // ── Click ─────────────────────────────────────────────────────

    _handleClick(e) {
        const pt = this._map.latLngToContainerPoint(e.latlng);
        let best = null, bestD = 18;

        for (const box of this._hitBoxes) {
            const d = Math.hypot(pt.x - box.x, pt.y - box.y);
            if (d < bestD) { bestD = d; best = box; }
        }

        if (best) {
            this._selected = best.id;
            this._scheduleDraw();
            this._onClick?.(best.data);
        } else {
            this._selected = null;
            this._scheduleDraw();
        }
    }
}
