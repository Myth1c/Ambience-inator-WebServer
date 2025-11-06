# web/embed/state_cache.py
"""Keeps a cached copy of the bot's current state for embeds and API routes."""

import threading

_state_lock = threading.Lock()
_latest_state = {
    "music": {"track_name": "Nothing Playing", "playlist_name": "None", "playing": False},
    "ambience": {"name": "None", "playing": False, "volume": 25},
    "in_vc": False,
    "bot_online": "offline"
}

def update_state(new_state: dict):
    """Safely update the cached playback state"""
    global _latest_state
    with _state_lock:
        _latest_state.update(new_state)
        
        
def get_state() -> dict:
    """Return a shallow copy of the latest known state"""
    with _state_lock:
        return dict(_latest_state)