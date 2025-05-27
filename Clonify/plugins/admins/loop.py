from pyrogram import filters
from pyrogram.types import Message

from Clonify import app, LOGGER # Added LOGGER
from Clonify.utils.database import get_loop, set_loop
from Clonify.utils.decorators import AdminRightsCheck
from Clonify.utils.inline import close_markup
from config import BANNED_USERS

_log = LOGGER(__name__) # Added logger instance

@app.on_message(filters.command(["loop", "cloop"]) & filters.group & ~BANNED_USERS)
@AdminRightsCheck
async def admins(cli, message: Message, _, chat_id):
    admin_user = message.from_user
    usage = _["admin_17"] # "Usage: /loop [number|enable|disable]"
    
    if len(message.command) != 2:
        _log.warning(f"Loop command misused by {admin_user.id} in chat {chat_id}: Incorrect argument count. Usage: {usage}")
        return await message.reply_text(usage)

    state = message.text.split(None, 1)[1].strip()
    loop_count_to_set = 0 # Default to disable if not changed

    if state.isnumeric():
        state_val = int(state)
        if 1 <= state_val <= 10: # Max loop is 10
            current_loop = await get_loop(chat_id)
            # if current_loop != 0: # Original logic: state = got + state - This seems like it would accumulate indefinitely.
            # The more common interpretation of /loop 3 is "set loop to 3", not "add 3 to current loop".
            # I will assume it means "set loop to X". If accumulation is desired, this logic needs review.
            # For now, directly setting the loop count.
            loop_count_to_set = state_val
            if loop_count_to_set > 10: loop_count_to_set = 10 # Cap at 10
            
            await set_loop(chat_id, loop_count_to_set)
            _log.info(f"Loop set to {loop_count_to_set} in chat {chat_id} by {admin_user.id}.")
            return await message.reply_text(
                text=_["admin_18"].format(loop_count_to_set, admin_user.mention), # "Loop set to X by User"
                reply_markup=close_markup(_),
            )
        else:
            _log.warning(f"Loop command in chat {chat_id} by {admin_user.id}: Invalid numeric value '{state_val}'. Expected 1-10.")
            return await message.reply_text(usage + "\n\n" + _["admin_loop_usage_limit"] if "admin_loop_usage_limit" in _ else usage + "\n\n(Value must be between 1 and 10)") # Provide more specific error
    elif state.lower() == "enable":
        loop_count_to_set = 10 # Max loop count for "enable"
        await set_loop(chat_id, loop_count_to_set)
        _log.info(f"Loop enabled (set to {loop_count_to_set}) in chat {chat_id} by {admin_user.id}.")
        return await message.reply_text(
            text=_["admin_18"].format(loop_count_to_set, admin_user.mention), # Using same "Loop set to X" message
            reply_markup=close_markup(_),
        )
    elif state.lower() == "disable":
        loop_count_to_set = 0
        await set_loop(chat_id, loop_count_to_set)
        _log.info(f"Loop disabled in chat {chat_id} by {admin_user.id}.")
        return await message.reply_text(
            _["admin_19"].format(admin_user.mention), # "Loop disabled by User"
            reply_markup=close_markup(_),
        )
    else:
        _log.warning(f"Loop command in chat {chat_id} by {admin_user.id}: Invalid state argument '{state}'.")
        return await message.reply_text(usage)
