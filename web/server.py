# web/server.py

import asyncio
from aiohttp import web
import signal

from web.ws_handlers import websocket_handler, broadcast_state_handler, ipc_bot_handler

global AUTH_KEY

async def handle_options(request):
    """Handle CORS preflight OPTIONS requests."""
    return web.Response(status=200, headers={
        "Access-Control-Allow-Origin": "https://myth1c.github.io",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Credentials": "true"
    })

@web.middleware
async def cors_middleware(request, handler):
    """Add CORS headers to every response."""
    if request.method == "OPTIONS":
        return await handle_options(request)

    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "https://myth1c.github.io"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@web.middleware
async def auth_middleware(request, handler):
    # Allow these paths to bypass the authentication step of the site
    if request.path in ("/auth", "/auth_check", "/ws", "/status", "/broadcast_state"):
        return await handler(request)

    # Check if already authenticated
    token = request.cookies.get("auth") or request.headers.get("Authorization")
    if token == AUTH_KEY:
        return await handler(request)

    # Otherwise, redirect to /auth
    return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

def create_app():
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
        
    # === Static + Page Routes ===
    app.router.add_get("/", lambda r: web.Response(text="Ambience-inator backend OK"))
    app.router.add_get("/setup", lambda r: web.Response(text="setup.html placeholder"))
    app.router.add_get("/edit", lambda r: web.Response(text="edit.html placeholder"))
    app.router.add_get("/play", lambda r: web.Response(text="playback.html placeholder"))
    app.router.add_get("/auth", lambda r: web.Response(text="auth.html placeholder"))
    
    # === API Routes ===
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
    app.router.add_get("/ws", websocket_handler)
    app.router.add_post("/broadcast_state", broadcast_state_handler)
    app.router.add_get("/ipc", ipc_bot_handler)
    
    # Allow options globally
    app.router.add_route("OPTIONS", "/{tail:.*}", handle_options)
    
    return app


async def start_server_async(host="0.0.0.0", port=8080, key=None):
    global AUTH_KEY
    AUTH_KEY = key

    print(f"[WEB-RUNNER] Auth Key set to {AUTH_KEY}")
    app = create_app()
    
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, port)
    await site.start()

    print(f"Web server running on http://{host}:{port}")

    # === Graceful Shutdown Handling ===
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

    # Wait for stop event (until container stop)
    await stop_event.wait()
    print("[WEB] Shutting down web server...")
    
    await runner.cleanup()
    print("[WEB] Server closed cleanly.")
    
    
