# web/embed/queue.py

import os
import time
import asyncio
from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

from web.embed.state_cache import get_state  # Uses your existing cache system


# === File paths ===
BASE_DIR = os.path.dirname(__file__)
CACHE_DIR = os.path.join(BASE_DIR, "cache")
TEMPLATE_DIR = BASE_DIR
CACHE_IMAGE_PATH = os.path.join(CACHE_DIR, "queue.png")

# === Initialize Jinja2 environment ===
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html'])
)

# Make sure cache directory exists since render starts with an empty file system
os.makedirs(CACHE_DIR, exist_ok=True)

async def generate_queue_image(state: dict):
    """
    Render a PNG preview of the current queue based on playback state.
    Called automatically when the bot sends a status_update.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    # --- Prepare data for template ---
    music = state.get("music", {})
    playlist_name = music.get("playlist_name", "Unknown Playlist")
    current_track = music.get("track_name", "Nothing Playing")
    shuffle = "On" if music.get("shuffle") else "Off"
    loop = "On" if music.get("loop") else "Off"
    volume = music.get("volume", 100)
    in_vc = "✅" if state.get("in_vc", False) else "❌"
    bot_status = state.get("bot_online", "unknown")

    # Format data to pass to template
    template_data = {
        "playlist_name": playlist_name,
        "current_track": current_track,
        "volume": volume,
        "shuffle": shuffle,
        "loop": loop,
        "in_vc": in_vc,
        "bot_status": bot_status,
        "timestamp": time.strftime("%H:%M:%S")
    }

    # --- Render template to HTML file ---
    template = env.get_template("queue_template.html")
    html_path = os.path.join(CACHE_DIR, "queue_render.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(template.render(**template_data))

    # --- Use Playwright to screenshot rendered HTML ---
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 600, "height": 315})
        await page.goto(f"file://{html_path}")
        await asyncio.sleep(0.3)  # allow CSS to render
        await page.screenshot(path=CACHE_IMAGE_PATH)
        await browser.close()

    print(f"[EMBED] Queue image updated at {time.ctime()}")


async def embed_queue_handler(request):
    """
    Serve the Discord-embed-compatible HTML page.
    This page includes OpenGraph meta tags for preview rendering.
    """
    state = get_state()
    music = state.get("music", {})
    track = music.get("track_name", "Nothing Playing")
    playlist = music.get("playlist_name", "Unknown Playlist")
    bot_status = state.get("bot_online", "unknown")

    image_url = f"{request.scheme}://{request.host}/embed/cache/queue.png?cb={int(time.time())}"

    html = f"""
    <html>
    <head>
        <meta property="og:title" content="🎵 Now Playing: {track}">
        <meta property="og:description" content="Playlist: {playlist} • Bot: {bot_status}">
        <meta property="og:image" content="{image_url}">
        <meta name="theme-color" content="#4caf50">
        <meta property="og:type" content="website">
    </head>
    <body style="background-color:#111; color:white; font-family:sans-serif; text-align:center;">
        <h2>🎶 {playlist}</h2>
        <p><strong>Now Playing:</strong> {track}</p>
        <img src="{image_url}" width="600" style="margin-top:10px;border-radius:8px;"/>
        <p style="font-size:12px;opacity:0.6;">Last updated at {time.ctime()}</p>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


_DEFAULT_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>Ambience-inator Queue</title>
        <style>
            body {{
                font-family: system-ui, sans-serif;
                background: linear-gradient(135deg, #1b1b1b, #2e2e2e);
                color: #fff;
                width: 600px;
                height: 315px;
                padding: 20px;
                box-sizing: border-box;
            }}
            h1 {{
                font-size: 22px; 
                margin: 0 0 8px 0; 
            }}
            p {{
                font-size: 15px; 
                margin: 6px 0; 
            }}
            .footer {{ 
                position:absolute;
                bottom:10px;
                right:20px;
                font-size:12px;
                opacity:0.5; 
            }}
        </style>
    </head>
        <body>
            <h1>🎶 {{ playlist_name }}</h1>
            <p><strong>Current Track:</strong> {{ current_track }}</p>
            <p><strong>Volume:</strong> {{ volume }}%</p>
            <p><strong>Shuffle:</strong> {{ shuffle }} | <strong>Loop:</strong> {{ loop }}</p>
            <p><strong>Voice Connected:</strong> {{ in_vc }} | <strong>Bot:</strong> {{ bot_status }}</p>
            <p class="footer">Updated {{ timestamp }}</p>
        </body>
    </html>
"""

# If template file doesn't exist, create it
template_path = os.path.join(BASE_DIR, "queue_template.html")
if not os.path.exists(template_path):
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(_DEFAULT_TEMPLATE)
