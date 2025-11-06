# web/ws_handlers.py

import aiohttp, json, asyncio

from aiohttp import web
from web.embed.state_cache import update_state, get_state
from web.embed.queue import generate_queue_image

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

async def ipc_bot_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_bots.add(ws)
    print("[WEB] Bot connected via IPC", flush=True)
    await ws.send_json({"type": "server_ack", "message": "Connected to Render backend"})

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                
                # Handle live state updates
                if payload.get("type") == "state_update" and "payload" in payload:
                    update_state(payload["payload"])
                    asyncio.create_task(generate_queue_image(get_state()))
                    print ("[WEB] Cached new playback state from bot")
                else:
                    print("[WEB] From bot:", msg.data, flush=True)
                    
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
            print("[WEB→BOT] Forwarding payload to bot:", payload)
            await ws.send_str(json.dumps(payload))
        except Exception:
            connected_bots.discard(ws)
            
async def forward_to_clients(payload):
    for ws in list(connections):
        try:
            print("[BOT→WEB] Forwarding payload to clients:", payload)
            await ws.send_str(json.dumps(payload))
        except Exception:
            connections.discard(ws)
            
async def heartbeat_handler(request):
    """Client heartbeat: checks if webserver and bot are alive."""
    bot_ok = False
    
    # Try pinging the bot via IP
    try:
        for ws in list(connected_bots):
            if ws.closed:
                continue
            await ws.send_json({"type": "heartbeat_check"})
            bot_ok = True
            break
    except Exception as e:
        print("[HEARTBEAT] IPC ping failed: ", e)
        
    return web.json_response({
        "ok": True,
        "bot_connected": bot_ok
    })