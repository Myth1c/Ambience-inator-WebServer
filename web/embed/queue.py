"""Handles generation of the Queue embed for Ambience-inator."""

import os
import time
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from web.embed.state_cache import get_state


# === Paths ===
BASE_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

QUEUE_IMG_PATH = os.path.join(CACHE_DIR, "queue.png")

# === Jinja2 Setup ===
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# Track last render time so we don’t rebuild constantly
_last_render_time = 0
RENDER_COOLDOWN = 30  # seconds


# === HTML Rendering ===
async def render_queue_html() -> str:
    """Render the queue HTML using Jinja2 and the cached playback state."""
    state = get_state()
    template = env.get_template("queue_template.html")
    return template.render(**state)


# === Screenshot Generation ===
async def generate_queue_image() -> str:
    """Generate (or overwrite) the queue image from rendered HTML."""
    html = await render_queue_html()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = await browser.new_page(viewport={"width": 640, "height": 400})
        await page.set_content(html)
        await page.screenshot(path=QUEUE_IMG_PATH)
        await browser.close()

    print(f"[EMBED] Queue image updated at {QUEUE_IMG_PATH}")
    return QUEUE_IMG_PATH


# === Routes ===
async def queue_embed_handler(request):
    """
    Handle GET /embed/queue
    If the cache image is older than RENDER_COOLDOWN, regenerate it.
    Then return the PNG directly.
    """
    global _last_render_time
    now = time.time()

    # Only regenerate if needed
    if not os.path.exists(QUEUE_IMG_PATH) or (now - _last_render_time) > RENDER_COOLDOWN:
        await generate_queue_image()
        _last_render_time = now

    return web.FileResponse(QUEUE_IMG_PATH)


async def queue_html_preview(request):
    """
    Handle GET /embed/queue/html
    Renders and returns the HTML view directly (for browser debugging).
    """
    html = await render_queue_html()
    return web.Response(text=html, content_type="text/html")


# === Router Registration Helper ===
def setup_routes(app: web.Application):
    """Register queue embed routes."""
    app.router.add_get("/embed/queue", queue_embed_handler)
    app.router.add_get("/embed/queue/html", queue_html_preview)
    print("[WEB] Queue embed routes registered")
