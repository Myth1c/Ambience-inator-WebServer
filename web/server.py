# web/server.py

import asyncio
from aiohttp import web
import aiohttp_cors
import signal

from web.ws_handlers import websocket_handler, broadcast_state_handler, broadcast_playback_state

global AUTH_KEY

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
    app = web.Application(middlewares=[auth_middleware])
    
    # ---- CORS SETUP ----
    cors = aiohttp_cors.setup(app, defaults={
        "https://myth1c.github.io": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "OPTIONS"],
        )
    })
    # ---------------------
    
    # === API Routes ===
    app.router.add_get("/ws", websocket_handler)
    
    # Endpoint to verify the key
    async def auth_check(request):
        data = await request.json()
        if data.get("key") == AUTH_KEY:
            response = web.json_response({"ok": True})
            response.set_cookie("auth", AUTH_KEY, httponly=True, max_age=86400)
            return response
        return web.json_response({"ok": False}, status=401)
    
    app.router.add_post("/auth_check", auth_check)
   
    # State broadcast endpoint
    app.router.add_post("/broadcast_state", broadcast_state_handler)
    
    # Root page for health check / debugging
    async def root_handler(request):
        return web.Response(
            text=(
                "Ambience-inator Web API is running.\n"
                "Frontend: https://myth1c.github.io/ambience-inator/"
            ),
            content_type="text/plain"
        )
    
    app.router.add_get("/", root_handler)
    
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
    
    
