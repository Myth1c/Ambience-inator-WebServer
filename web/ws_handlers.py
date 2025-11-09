# web/ws_handlers.py

import aiohttp, json, asyncio, os

from aiohttp import web

# ============================
# Connection sets
# ============================
connections = set()       # Connected web clients
connected_bots = set()    # Connected IPC bots

# Commands allowed for unauthenticated users
READ_ONLY_COMMANDS = {
    "GET_PLAYLISTS",
    "GET_AMBIENCE",
    "GET_PLAYBACK_STATE",
    "GET_BOT_STATUS"
}

# ============================
# Unified non-blocking WS send
# ============================
async def ws_send(ws, payload):
    """
    Fire-and-forget WS send. Never blocks.
    Ensures disconnected sockets are removed.
    """
    async def _send():
        try:
            if not ws.closed:
                await ws.send_str(json.dumps(payload))
        except Exception:
            # Clean up dead connections
            connections.discard(ws)
            connected_bots.discard(ws)

    asyncio.create_task(_send())


# ============================
# Web ↔ Client handler
# ============================
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connections.add(ws)
    print("[WS] Client connected")

    # Check cookie or header
    auth_cookie = request.cookies.get("auth") or request.headers.get("Authorization")
    authorized = (auth_cookie == os.getenv("AUTH_KEY"))

    if not authorized:
        print("[WS] Unauthorized client connected — command restrictions applied.")

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:

                # Parse message
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    print("[WS] Non-JSON message ignored.")
                    continue

                print("[WS] Received:", data)

                cmd = data.get("command")

                if not authorized:
                    if cmd in READ_ONLY_COMMANDS:
                        await ws_send(ws, {"ok": True, "response": "read_only_mode"})
                    else:
                        await ws_send(ws, {
                            "ok": False,
                            "command": cmd,
                            "error": "UNAUTHORIZED"
                        })
                        continue

                # ============================
                # Authorized or sending an allowed command
                # ============================
                await forward_to_bots(data)

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("[WS] Error:", ws.exception())

    finally:
        connections.discard(ws)
        print("[WS] Client disconnected")

    return ws


# ============================
# Bot ↔ Web IPC handler
# ============================
async def ipc_bot_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_bots.add(ws)
    print("[WEB] Bot connected via IPC")

    await ws_send(ws, {
        "type": "server_ack",
        "message": "Connected to Render backend"
    })

    async for msg in ws:
        try:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                except json.JSONDecodeError:
                    print("[WEB] Bad JSON from bot")
                    continue

                print("[WEB] From bot:", payload)

                try:
                    await forward_to_clients(payload)
                except Exception as e:
                    print("[WEB] ERROR in forward_to_clients:", e)
                    continue

            elif msg.type == web.WSMsgType.ERROR:
                print("[WEB] IPC WS error:", ws.exception())

        except Exception as e:
            print("[WEB] Unhandled WS error:", e)

    return ws


# ============================
# Send routing helpers
# ============================
async def forward_to_bots(payload):
    """Forward a client message to all connected bots."""
    for ws in list(connected_bots):
        await ws_send(ws, payload)

async def forward_to_clients(payload):
    """Forward bot message to all connected clients."""
    for ws in list(connections):
        await ws_send(ws, payload)


# ============================
# Heartbeat endpoint
# ============================
async def heartbeat_handler(request):
    """Client heartbeat: checks if webserver and at least one bot are alive."""
    bot_ok = False

    try:
        for ws in list(connected_bots):
            if ws.closed:
                continue
            await ws_send(ws, {"type": "heartbeat_check"})
            bot_ok = True
            break

    except Exception as e:
        print("[HEARTBEAT] IPC ping failed:", e)

    return web.json_response({
        "ok": True,
        "bot_connected": bot_ok
    })
