"""
WebSocket broadcaster — sends anomaly alerts to connected browsers.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class Broadcaster:
    _clients: set[WebSocket] = field(default_factory=set)

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.add(ws)
        print(f"[WS] client connected  ({len(self._clients)} total)")

    def disconnect(self, ws: WebSocket):
        self._clients.discard(ws)
        print(f"[WS] client disconnected  ({len(self._clients)} total)")

    async def broadcast(self, message: dict):
        """Send JSON message to all connected clients."""
        if not self._clients:
            return
        payload = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in self._clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)

    @property
    def client_count(self) -> int:
        return len(self._clients)
