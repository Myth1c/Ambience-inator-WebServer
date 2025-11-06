"""Handles generation of the Queue embed for Ambience-inator."""

import os, json
from aiohttp import web
from jinja2 import Environment, FileSystemLoader, Template
from playwright.async_api import async_playwright
from web.embed.state_cache import get_state


# === Paths ===
BASE_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_IMG = os.path.join(CACHE_DIR, "queue_preview.png")
TEMPLATE_FILE = os.path.join(TEMPLATE_DIR, "queue_template.html")

# === Jinja2 Setup ===
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


# === HTML Rendering ===
async def render_queue_html() -> str:
    """Render the queue HTML using Jinja2 and the cached playback state."""
    state = get_state()
    template = env.get_template("queue_template.html")
    return template.render(state=state)


# === Generate Screenshot from HTML ===
async def generate_queue_image():
    """Render queue_template.html (with state) and capture a screenshot."""
    rendered_html = await render_queue_html()

    tmp_path = os.path.join(CACHE_DIR, "queue_render.html")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()
            await page.goto(f"file://{tmp_path}")
            await page.screenshot(path=CACHE_IMG, full_page=True)
            await browser.close()

        print(f"[EMBED] Updated queue preview at {CACHE_IMG}")
        return CACHE_IMG
    except Exception as e:
        print(f"[EMBED] Failed to render image queue: {e}")
        return None



# === Route Handler ===
async def queue_embed_handler(request):
    """Display a simple HTML or PNG of the current playback queue."""
    mode = request.query.get("format", "html")

    if mode == "image":
        if not os.path.exists(CACHE_IMG):
            await generate_queue_image()
        return web.FileResponse(CACHE_IMG)

    # Otherwise render a live HTML preview using Jinja2
    html = await render_queue_html()
    return web.Response(text=html, content_type="text/html")


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
