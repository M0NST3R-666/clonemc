from pyrogram import filters
from pyrogram.types import Message

from Clonify import app, LOGGER # Added LOGGER
from Clonify.core.call import PRO
from Clonify.utils.database import is_music_playing, music_off
from Clonify.utils.decorators import AdminRightsCheck
from Clonify.utils.inline import close_markup
from config import BANNED_USERS

_log = LOGGER(__name__) # Added logger instance

@app.on_message(filters.command(["pause", "cpause"]) & filters.group & ~BANNED_USERS)
@AdminRightsCheck
async def pause_admin(cli, message: Message, _, chat_id):
    admin_user = message.from_user
    _log.info(f"Pause command received in chat {chat_id} by user {admin_user.id} ('{admin_user.first_name}').")
    
    if not await is_music_playing(chat_id):
        _log.warning(f"Pause command in chat {chat_id}: No music playing.")
        return await message.reply_text(_["admin_1"])
    
    try:
        await music_off(chat_id) # DB update
        await PRO.pause_stream(chat_id) # Actual PyTgCalls action
        _log.info(f"Music paused successfully in chat {chat_id} by {admin_user.id}.")
        await message.reply_text(
            _["admin_2"].format(admin_user.mention), reply_markup=close_markup(_)
        )
    except Exception as e:
        # PRO.pause_stream should ideally raise specific exceptions we can catch.
        # For now, a general catch. The error handling in PRO.pause_stream itself was improved.
        _log.error(f"Error during pause sequence in chat {chat_id} initiated by {admin_user.id}: {type(e).__name__} - {e}")
        # Notify user about the error if possible/needed
        await message.reply_text(_["admin_error"].format(e) if "admin_error" in _ else f"An error occurred: {e}")
