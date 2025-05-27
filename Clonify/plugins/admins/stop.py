from pyrogram import filters
from pyrogram.types import Message

from Clonify import app, LOGGER # Added LOGGER
from Clonify.core.call import PRO
from Clonify.utils.database import set_loop
from Clonify.utils.decorators import AdminRightsCheck
from Clonify.utils.inline import close_markup
from config import BANNED_USERS

_log = LOGGER(__name__) # Added logger instance

@app.on_message(
    filters.command(["end", "stop", "cend", "cstop"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def stop_music(cli, message: Message, _, chat_id):
    admin_user = message.from_user
    _log.info(f"Stop command received in chat {chat_id} by user {admin_user.id} ('{admin_user.first_name}').")

    if not len(message.command) == 1: # Ignore if command has arguments like /stop some_text
        _log.warning(f"Stop command in chat {chat_id} by {admin_user.id} had extra arguments: {message.text}. Ignoring args.")
        # Proceed with stop functionality anyway, as user intent is clear.

    try:
        await PRO.stop_stream(chat_id) # This should internally handle _clear_ and other cleanup.
        await set_loop(chat_id, 0) # Reset loop state
        _log.info(f"Stream stopped and loop set to 0 in chat {chat_id} by {admin_user.id}.")
        await message.reply_text(
            _["admin_5"].format(admin_user.mention), reply_markup=close_markup(_)
        )
    except Exception as e:
        # PRO.stop_stream is expected to have its own robust logging.
        # This catch is for unexpected errors during the stop sequence in this plugin.
        _log.error(f"Error during stop sequence in chat {chat_id} initiated by {admin_user.id}: {type(e).__name__} - {e}")
        # Try to inform user, though PRO.stop_stream might have already if it's a py-tgcalls issue.
        await message.reply_text(_["admin_error"].format(e) if "admin_error" in _ else f"An error occurred while stopping: {e}")
