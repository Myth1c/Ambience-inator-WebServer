# web/embed/state_cache.py
"""Keeps a cached copy of the bot's current state for embeds and API routes."""

_latest_state = {
    "music": {"track_name": "Nothing Playing", "playlist_name": "None", "playing": False},
    "ambience": {"name": "None", "playing": False, "volume": 25},
    "in_vc": False,
    "bot_online": "offline"
}
_latest_queue_state = {
    "playlist_name": "None",
    "tracks": [], #list of {"name" : str, "url" : sr}
    "current_index": 0,
    "previous_stack" : [], #list of indexes, helpful in case it goes out of order somehow
    "loop_current" : False
}

# ===== Playback State =====
def update_state(new_state: dict):
    """Save the bot playback state."""
    global _latest_state
    _latest_state.update(new_state)


def get_state() -> dict:
    """Return a dict of bot playback state."""
    return dict(_latest_state)


# ===== Queue State =====
def set_queue_state(new_state: dict):
    """Save the full queue information."""
    global _latest_queue_state
    _latest_queue_state.update(new_state)


def get_queue_state() -> dict:
    """Return a dict of playlist queue info."""
    return dict(_latest_queue_state)