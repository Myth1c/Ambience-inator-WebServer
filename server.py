# web/server.py

import asyncio
from aiohttp import web
import pathlib
import signal

from ws_handlers import websocket_handler, broadcast_state_handler, broadcast_playback_state

BASE_DIR = pathlib.Path(__file__).parent.parent # root folder
PUBLIC_DIR = BASE_DIR / "ui" / "public"

global AUTH_KEY

@web.middleware
async def auth_middleware(request, handler):
    # Allow static files, websocket, and auth endpoints
    if request.path.startswith("/public") or request.path in ("/auth", "/auth_check", "/ws", "/status"):
        return await handler(request)

    # Check if already authenticated
    token = request.cookies.get("auth") or request.headers.get("Authorization")
    if token == AUTH_KEY:
        return await handler(request)

    # Otherwise, redirect to /auth
    raise web.HTTPFound("/auth")

def create_app():
    app = web.Application(middlewares=[auth_middleware])
    
    # Web UI routes
    app.router.add_get("/", lambda r: web.FileResponse( PUBLIC_DIR / "index.html"))
    app.router.add_get("/setup", lambda r: web.FileResponse(PUBLIC_DIR / "setup.html"))
    app.router.add_get("/edit", lambda r: web.FileResponse(PUBLIC_DIR / "edit.html"))
    app.router.add_get("/play", lambda r: web.FileResponse(PUBLIC_DIR / "playback.html"))
    app.router.add_get("/auth", lambda r: web.FileResponse(PUBLIC_DIR / "auth.html"))
    app.router.add_static("/public/", path=PUBLIC_DIR, name="static")
    
    
    # Endpoint to verify the key
    async def auth_check(request):
        data = await request.json()
        if data.get("key") == AUTH_KEY:
            response = web.json_response({"ok": True})
            response.set_cookie("auth", AUTH_KEY, httponly=True, max_age=86400)
            return response
        return web.json_response({"ok": False}, status=401)
    
    # WebSocket route
    app.router.add_get("/ws", websocket_handler)
    
    
    app.router.add_post("/auth_check", auth_check)
    app.router.add_post("/broadcast_state", broadcast_state_handler)
    
    return app


async def start_server_async(host="0.0.0.0", port=8080, key=None):
    global AUTH_KEY
    AUTH_KEY = key

    print(f"Auth Key set to {AUTH_KEY}")
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, port)
    await site.start()

    print(f"Web server running on http://{host}:{port}")

    # --- graceful shutdown handling ---
    stop_event = asyncio.Event()

    def _handle_signal():
        print("[WEB] Shutdown signal received.")
        stop_event.set()

    # Register signals (works on Linux/Mac; on Windows Docker, it’s handled via Docker stop)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Signal handlers not available (Windows)
            pass

    # Wait for stop event (until container stop)
    await stop_event.wait()

    print("[WEB] Shutting down web server...")
    await runner.cleanup()
    print("[WEB] Server closed cleanly.")
