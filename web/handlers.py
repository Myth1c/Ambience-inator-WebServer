from web.ws_handlers import set_bot_command_handler, send_bot_command, broadcast_playback_state

async def handle_ws_command(data, ws):
    command = data.get("command")
    args = {k: v for k, v in data.items() if k != "command"}

    # Forward every command to the bot container via IPC
    result = await send_bot_command(command, args)

    # If playback state was returned, broadcast to all clients
    if result.get("state"):
        await broadcast_playback_state(lambda: result["state"])

    return result

# Register the handler globally
set_bot_command_handler(handle_ws_command)
