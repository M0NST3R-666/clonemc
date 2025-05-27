from pyrogram import filters
from pyrogram.types import Message

from Clonify import app, LOGGER # Added LOGGER
from Clonify.core.call import PRO
from Clonify.utils.database import is_music_playing, music_on
from Clonify.utils.decorators import AdminRightsCheck
from Clonify.utils.inline import close_markup
from config import BANNED_USERS

_log = LOGGER(__name__) # Added logger instance

@app.on_message(filters.command(["resume", "cresume"]) & filters.group & ~BANNED_USERS)
@AdminRightsCheck
async def resume_com(cli, message: Message, _, chat_id):
    admin_user = message.from_user
    _log.info(f"Resume command received in chat {chat_id} by user {admin_user.id} ('{admin_user.first_name}').")

    if await is_music_playing(chat_id):
        _log.warning(f"Resume command in chat {chat_id}: Music already playing.")
        return await message.reply_text(_["admin_3"])
    
    try:
        await music_on(chat_id) # DB update
        await PRO.resume_stream(chat_id) # Actual PyTgCalls action
        _log.info(f"Music resumed successfully in chat {chat_id} by {admin_user.id}.")
        await message.reply_text(
            _["admin_4"].format(admin_user.mention), reply_markup=close_markup(_)
        )
    except Exception as e:
        # PRO.resume_stream should ideally raise specific exceptions.
        # Error handling in PRO.resume_stream itself was improved.
        _log.error(f"Error during resume sequence in chat {chat_id} initiated by {admin_user.id}: {type(e).__name__} - {e}")
        await message.reply_text(_["admin_error"].format(e) if "admin_error" in _ else f"An error occurred: {e}")
