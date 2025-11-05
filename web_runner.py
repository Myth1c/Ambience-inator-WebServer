# web_runner.py

import asyncio
import os
from web.server import start_server_async
from web.handlers import handle_ws_command # ensures it registers with ws_handlers

async def main():
    print("[WEB-RUNNER] Starting Ambience-inator Web Server...")

    # Environment variables (from docker-compose)
    AUTH_KEY = os.getenv("AUTH_KEY")
    HOST_IP = os.getenv("HOST_IP", "0.0.0.0")
    HOST_PORT = int(os.getenv("HOST_PORT", "8080"))

    if not AUTH_KEY:
        raise RuntimeError("AUTH_KEY environment variable not set")

    # Start the aiohttp web server
    await start_server_async(
        host=HOST_IP,
        port=HOST_PORT,
        key=AUTH_KEY
    )

    print(f"[WEB-RUNNER] Web server running on http://{HOST_IP}:{HOST_PORT}")

if __name__ == "__main__":
    asyncio.run(main())
