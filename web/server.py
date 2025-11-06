# web/server.py

import asyncio
from aiohttp import web
import signal

from web.ws_handlers import websocket_handler, ipc_bot_handler, heartbeat_handler

global AUTH_KEY

ALLOWD_ORIGINS = [
    "https://myth1c.github.io",
    "http://localhost",
    "http://127.0.0.1"
]

# ===== Middleware =====
@web.middleware
async def cors_middleware(request, handler):
    """Add CORS headers to every response."""
    
    origin = request.headers.get("Origin")
    if origin in ALLOWD_ORIGINS:
        allow_origin = origin
    else:
        allow_origin = "https://myth1c.github.io"
        
    if request.method == "OPTIONS":
        return web.Response(status=200, headers={
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true"
        })
    
    
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = allow_origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    
    return response

@web.middleware
async def auth_middleware(request, handler):
    # Allow these paths to bypass the authentication step of the site
    if request.path in ("/auth", "/auth_check", "/ws", "/status", "/ipc", "/heartbeat"):
        return await handler(request)

    # Check if already authenticated
    token = request.cookies.get("auth") or request.headers.get("Authorization")
    if token == AUTH_KEY:
        return await handler(request)

    # Otherwise, redirect to /auth
    return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

def create_app():
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
        
    # --- Health check ---
    app.router.add_get("/", lambda r: web.Response(text="Ambience-inator backend OK"))
    
    # --- Auth route ---
    async def auth_check(request):
        cookie = request.cookies.get("auth")
        if cookie == AUTH_KEY:
            return web.json_response({"ok": True})

        try:
            data = await request.json()
        except Exception:
            data = {}

        if data.get("key") == AUTH_KEY:
            response = web.json_response({"ok": True})
            response.set_cookie(
                "auth",
                AUTH_KEY,
                httponly=True,
                secure=True,
                samesite="None",
                max_age=86400,
                path="/"
            )
            return response

        return web.json_response({"ok": False}, status=401)
        
    app.router.add_post("/auth_check", auth_check)
    
    # --- WebSocket endpoints ---
    app.router.add_get("/ws", websocket_handler)
    app.router.add_get("/ipc", ipc_bot_handler)
    app.router.add_get("/heartbeat", heartbeat_handler)
    
    return app


# ===== Entry Point =====
async def start_server_async(host="0.0.0.0", port=8080, key=None):
    global AUTH_KEY
    AUTH_KEY = key

    print(f"[WEB-RUNNER] Auth Key set to {AUTH_KEY}")
    app = create_app()
    
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, port)
    await site.start()

    # --- Graceful Shutdown Handling ---
    stop_event = asyncio.Event()

    def _handle_signal():
        print("[WEB] Shutdown signal received.")
        stop_event.set()

    # Register signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    await stop_event.wait()
    print("[WEB] Shutting down web server...")
    
    await runner.cleanup()
    print("[WEB] Server closed cleanly.")
    
    
