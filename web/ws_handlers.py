# web/ws_handlers.py

from aiohttp import web
import aiohttp
import json
import asyncio

BOT_IPC_URL = "http://ambience-bot:8765/bot_command"
connections = set()
connected_bots = set()
bot_command_handler = None

def set_bot_command_handler(handler):
    global bot_command_handler
    bot_command_handler = handler

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
                
                
                if bot_command_handler:
                    result = await bot_command_handler(data, ws)
                    if result is None:
                        result = {"ack": True, "received": data}            
                    await ws.send_json(result)
                else:
                    # Just echo for now if no valid command
                    await ws.send_json({"ack": True, "received": data})
                
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

async def send_bot_command(command, args=None):
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"command": command, "args": args or {}}
            async with session.post(BOT_IPC_URL, json=payload) as resp:
                data = await resp.json()
                print(f"[WEB→BOT] Sent {command} → got {data}")
                return data
    except Exception as e:
        print(f"[WEB→BOT] Error sending command {command}: {e}")
        return {"ok": False, "error": str(e)}
    
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
    print("[WEB] Bot connected via IPC")
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                print("[WEB] From bot:", msg.data)
                
    finally:
        connected_bots.remove(ws)
        print("[WEB] Bot disconnected")
        
    return ws