"""WebSocket endpoint for real-time updates."""

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Connected clients
_clients: list[WebSocket] = []


async def broadcast(event_type: str, data: dict):
    """Broadcast an event to all connected WebSocket clients."""
    message = json.dumps({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    disconnected = []
    for ws in _clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _clients.remove(ws)


@router.websocket("/live")
async def websocket_live(ws: WebSocket):
    """Live feed of balance updates, alerts, and forecast changes."""
    await ws.accept()
    _clients.append(ws)

    try:
        # Send welcome message
        await ws.send_text(json.dumps({
            "type": "connected",
            "data": {"message": "Connected to LiquidMind live feed"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))

        # Keep connection alive
        while True:
            try:
                # Wait for client messages (heartbeat/commands)
                data = await asyncio.wait_for(ws.receive_text(), timeout=30)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # Send heartbeat
                await ws.send_text(json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }))

    except WebSocketDisconnect:
        pass
    finally:
        if ws in _clients:
            _clients.remove(ws)
