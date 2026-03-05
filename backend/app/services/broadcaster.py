"""
WebSocket Connection Manager — broadcasts state to all connected clients.
Thread-safe via asyncio; no locks needed (single event loop).
"""
from __future__ import annotations
import json
import logging
from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    """Manages all active WebSocket connections and broadcasts."""

    def __init__(self) -> None:
        self._active: set[WebSocket] = set()

    # ── Connection lifecycle ───────────────────────────────────────

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._active.add(ws)
        log.info("WS client connected. Total: %d", len(self._active))

    def disconnect(self, ws: WebSocket) -> None:
        self._active.discard(ws)
        log.info("WS client disconnected. Total: %d", len(self._active))

    # ── Broadcast ─────────────────────────────────────────────────

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to every connected client.
        Dead connections are silently removed."""
        if not self._active:
            return

        data = json.dumps(message, separators=(",", ":"))  # compact
        dead: set[WebSocket] = set()

        for ws in self._active:
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)

        # Prune dead connections
        self._active -= dead
        if dead:
            log.debug("Removed %d dead WS connections", len(dead))

    async def send_to(self, ws: WebSocket, message: dict) -> None:
        """Send a JSON message to a single client (e.g. on first connect)."""
        try:
            await ws.send_text(json.dumps(message, separators=(",", ":")))
        except Exception as exc:
            log.warning("Failed to send to client: %s", exc)
            self.disconnect(ws)

    # ── Stats ─────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return len(self._active)


# App-wide singleton
manager = ConnectionManager()
