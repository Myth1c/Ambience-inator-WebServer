# web/embed/queue.py

from aiohttp import web
from web.embed.state_cache import get_state

async def embed_queue(request):
    """Dynamic embed using the latest cached bot state"""
    
    state = await get_state()
    music = state.get("music", {})
    bot_online = state.get("bot_online", "offline")
    in_vc = state.get("in_vc", False)
    
    title = music.get("track_name", "Nothing Playing")
    playlist = music.get("playlist_name", "Unknown Playlist")
    playing = "Playing" if music.get("playing") else "Paused"
    status_text = f"Bot: {bot_online} | VC: {in_vc}"
    
    
    html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <title>Ambience-inator — Now Playing</title>

            <meta property="og:title" content="🎵 {title}">
            <meta property="og:description" content="{playing} • Playlist: {playlist} | {status_text}">
            <meta property="og:image" content="https://myth1c.github.io/Ambience-inator/images/embed-nowplaying.png">
            <meta property="og:type" content="website">

            <style>
                body {{
                    background: #0e0e10;
                    color: #e3e3e3;
                    font-family: 'Segoe UI', sans-serif;
                    text-align: center;
                    padding-top: 4rem;
                }}
                .card {{
                    display: inline-block;
                    background: #1e1f22;
                    padding: 2rem 3rem;
                    border-radius: 1rem;
                    box-shadow: 0 0 15px #000;
                }}
                .title {{
                    color: #00bfa5;
                    font-size: 1.4rem;
                    font-weight: bold;
                }}
                .info {{
                    margin-top: 0.8rem;
                    color: #ccc;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="title">Now Playing</div>
                <div class="info">{title}</div>
                <div class="info">Playlist: {playlist}</div>
                <div class="info">{status_text}</div>
            </div>
        </body>
        </html>
    """

    return web.Response(text=html, content_type="text/html")

def register_routes(app: web.Application):
    app.router.add_get("/embed/queue", embed_queue)