# web/ws_handlers.py

from aiohttp import web
import aiohttp
import json
import asyncio

connections = set()
connected_bots = set()

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    connections.add(ws)
    print("[WS] Client connected")
    
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                print("[WS] Received: ", data)
                
                # Forward client command to bots
                await forward_to_bots(data)                
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("[WS] Error: ", ws.exception())
                                
    finally:
        connections.remove(ws)
        print("[WS] client disconnected")
        
    return ws

async def broadcast_playback_state(get_state_func):
    """Send the latest playback state to all connected WebSocket clients.
    Automatically removes closed connections from the global connection list.
    """
    possible_state = get_state_func()
    state = await possible_state if asyncio.iscoroutine(possible_state) else possible_state


    stale_connections = []
    for ws in list(connections):
        if ws.closed:
            stale_connections.append(ws)
            continue

        try:
            await ws.send_json(state)
        except ConnectionResetError:
            print("[WS] Connection reset by peer")
            stale_connections.append(ws)
        except Exception as e:
            print(f"[WS] Broadcast error: {e}")
            stale_connections.append(ws)

    # Cleanup closed sockets
    for ws in stale_connections:
        connections.discard(ws)

    if stale_connections:
        print(f"[WS] Cleaned up {len(stale_connections)} stale connection(s)")

async def broadcast_state_handler(request):
    """Handle POSTs from the bot process to fan out updates to WS clients."""
    data = await request.json()
    print("[WEB] Received playback state update from bot")

    stale = []
    for ws in list(connections):
        if ws.closed:
            stale.append(ws)
            continue
        try:
            await ws.send_json(data)
        except Exception:
            stale.append(ws)

    for ws in stale:
        connections.discard(ws)
    return web.Response(text="OK")

async def ipc_bot_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_bots.add(ws)
    print("[WEB] Bot connected via IPC", flush=True)
    await ws.send_json({"type": "server_ack", "message": "Connected to Render backend"})

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                print("[WEB] From bot:", msg.data, flush=True)
                try:
                    payload = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                
                await forward_to_clients(payload)
                
            elif msg.type == web.WSMsgType.ERROR:
                print("[WEB] IPC WS error:", ws.exception(), flush=True)
    finally:
        connected_bots.discard(ws)
        print("[WEB] Bot disconnected", flush=True)

    return ws


async def forward_to_bots(payload):
    for ws in list(connected_bots):
        try:
            await ws.send_str(json.dumps(payload))
        except Exception:
            connected_bots.discard(ws)
            
async def forward_to_clients(payload):
    for ws in list(connections):
        try:
            await ws.send_str(json.dumps(payload))
        except Exception:
            connections.discard(ws)
            
