from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from Clonify import app, LOGGER # Added LOGGER
from Clonify.misc import SUDOERS, db
from Clonify.utils.database import (
    get_authuser_names,
    get_cmode,
    get_lang,
    get_upvote_count,
    is_active_chat,
    is_maintenance,
    is_nonadmin_chat,
    is_skipmode,
)
from config import SUPPORT_CHAT, adminlist, confirmer # adminlist, confirmer are global dicts
from strings import get_string

from ..formatters import int_to_alpha

_log = LOGGER(__name__) # Added logger instance

def AdminRightsCheck(mystic):
    """Decorator to check for admin rights or if user is a sudoer for a command."""
    async def wrapper(client, message):
        user = message.from_user
        chat = message.chat
        func_name = mystic.__name__
        
        _log.debug(f"AdminRightsCheck decorator called for '{func_name}' by user {user.id} in chat {chat.id}.")

        if await is_maintenance() is False:
            if user.id not in SUDOERS:
                _log.warning(f"Maintenance mode ON. User {user.id} (not sudoer) blocked by AdminRightsCheck for '{func_name}' in chat {chat.id}.")
                return await message.reply_text(
                    text=f"{app.mention} ɪs ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ, ᴠɪsɪᴛ <a href={SUPPORT_CHAT}>sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ</a> ғᴏʀ ᴋɴᴏᴡɪɴɢ ᴛʜᴇ ʀᴇᴀsᴏɴ.",
                    disable_web_page_preview=True,
                )

        try:
            await message.delete()
            _log.debug(f"Deleted original message {message.id} in chat {chat.id} (AdminRightsCheck).")
        except Exception as e_del:
            _log.warning(f"Failed to delete message {message.id} in chat {chat.id} (AdminRightsCheck): {e_del}")

        try:
            language = await get_lang(chat.id)
            _ = get_string(language)
        except Exception as e_lang: # Should not happen if get_lang has defaults
            _log.error(f"Error getting language for chat {chat.id} in AdminRightsCheck: {e_lang}. Defaulting to 'en'.")
            _ = get_string("en")

        if message.sender_chat:
            _log.warning(f"Command '{func_name}' invoked by sender_chat {message.sender_chat.id} ('{message.sender_chat.title}') in chat {chat.id}. Replying with anonymous admin info.")
            upl = InlineKeyboardMarkup([[InlineKeyboardButton(text="ʜᴏᴡ ᴛᴏ ғɪx ?", callback_data="PROmousAdmin")]])
            return await message.reply_text(_["general_3"], reply_markup=upl) # "You are an anonymous admin..."

        # Determine target chat_id for channel play mode
        target_chat_id = chat.id
        is_channel_play = message.command and message.command[0][0] == "c"
        if is_channel_play:
            target_chat_id = await get_cmode(chat.id) # Fetches connected channel ID
            if target_chat_id is None:
                _log.warning(f"Channel play mode (c-command) used in chat {chat.id} but no channel is connected.")
                return await message.reply_text(_["setting_7"]) # "Channel play mode not set"
            try:
                await app.get_chat(target_chat_id) # Validate channel existence/access
                _log.debug(f"Channel play mode target chat is {target_chat_id} for command in {chat.id}.")
            except Exception as e_get_chat:
                _log.error(f"Failed to get_chat for connected channel ID {target_chat_id} (original chat {chat.id}): {e_get_chat}")
                return await message.reply_text(_["cplay_4"]) # "Error with connected channel"
        
        if not await is_active_chat(target_chat_id):
            _log.warning(f"Command '{func_name}' requires active VC in chat {target_chat_id}, but not active. User: {user.id}.")
            return await message.reply_text(_["general_5"]) # "No active VC"

        # Permission checks
        is_auth_chat = await is_nonadmin_chat(chat.id) # True if /auth on (anyone can use commands)
        if not is_auth_chat: # If /auth is OFF, then admin/sudo checks apply
            if user.id not in SUDOERS:
                current_adminlist = adminlist.get(chat.id, []) # Get admins for this chat from global dict
                if not current_adminlist: # No admins in cache for this chat
                    _log.warning(f"User {user.id} (not sudoer, not in adminlist) tried '{func_name}' in chat {chat.id}. Adminlist empty/not found.")
                    return await message.reply_text(_["admin_13"]) # "No admins in this chat"
                
                if user.id not in current_adminlist:
                    _log.info(f"User {user.id} (not sudoer, not in adminlist) trying restricted command '{func_name}' in chat {chat.id}.")
                    if await is_skipmode(target_chat_id): # Vote mode for skip
                        upvote_needed = await get_upvote_count(target_chat_id)
                        text = _["admin_vote_needed"].format(upvote_needed) if "admin_vote_needed" in _ else \
                               f"<b>ᴀᴅᴍɪɴ ʀɪɢʜᴛs ɴᴇᴇᴅᴇᴅ</b>\nʀᴇғʀᴇsʜ ᴀᴅᴍɪɴ ᴄᴀᴄʜᴇ ᴠɪᴀ : /reload\n\n» {upvote_needed} ᴠᴏᴛᴇs ɴᴇᴇᴅᴇᴅ ғᴏʀ ᴘᴇʀғᴏʀᴍɪɴɢ ᴛʜɪs ᴀᴄᴛɪᴏɴ."
                        
                        command_base = message.command[0]
                        if is_channel_play: command_base = command_base[1:] # remove 'c' prefix
                        
                        if command_base == "speed": # Specific commands might not support voting
                            _log.debug(f"Speed command by non-admin {user.id} in chat {chat.id} does not support voting.")
                            return await message.reply_text(_["admin_14"]) # "You are not allowed"

                        MODE_for_callback = command_base.title()
                        vote_callback_data = f"ADMIN UpVote|{target_chat_id}_{MODE_for_callback}"
                        vote_button = InlineKeyboardMarkup([[InlineKeyboardButton(text="ᴠᴏᴛᴇ", callback_data=vote_callback_data)]])
                        
                        # Store confirmation data for the vote
                        if target_chat_id not in confirmer: confirmer[target_chat_id] = {}
                        try:
                            # This assumes db[chat_id] is available and populated, which might not be true
                            # if the command is, for example, /pause when nothing is playing.
                            # This part needs careful review for context.
                            current_playing_track = db.get(target_chat_id) # list of dicts
                            if not current_playing_track:
                                 _log.warning(f"Vote requested by {user.id} for {MODE_for_callback} in chat {target_chat_id}, but queue is empty.")
                                 return await message.reply_text(_["admin_14"]) # Not allowed if nothing playing

                            vidid = current_playing_track[0]["vidid"]
                            file_path = current_playing_track[0]["file"]
                        except (IndexError, KeyError) as e_db_access:
                            _log.error(f"Error accessing db for vote confirmation data in chat {target_chat_id}: {e_db_access}. Command: {MODE_for_callback}")
                            return await message.reply_text(_["admin_14"]) # "You are not allowed / Error"

                        sent_message = await message.reply_text(text, reply_markup=vote_button)
                        confirmer[target_chat_id][sent_message.id] = {"vidid": vidid, "file": file_path}
                        _log.info(f"Vote initiated for action '{MODE_for_callback}' in chat {target_chat_id} by non-admin {user.id}. Message ID: {sent_message.id}")
                        return # Stop further execution, wait for vote
                    else: # Skipmode is OFF (immediate skip not allowed for non-admins)
                        _log.info(f"User {user.id} (non-admin) blocked by AdminRightsCheck (skipmode OFF) for '{func_name}' in chat {chat.id}.")
                        return await message.reply_text(_["admin_14"]) # "You are not allowed"
        
        _log.debug(f"AdminRightsCheck PASSED for user {user.id} running '{func_name}' in chat {chat.id} (target: {target_chat_id}).")
        return await mystic(client, message, _, target_chat_id) # Pass target_chat_id to the wrapped function

    return wrapper


def AdminActual(mystic):
    """Decorator for commands requiring actual admin privileges (can_manage_video_chats) or sudo."""
    async def wrapper(client, message):
        user = message.from_user
        chat = message.chat
        func_name = mystic.__name__
        _log.debug(f"AdminActual decorator called for '{func_name}' by user {user.id} in chat {chat.id}.")

        if await is_maintenance() is False:
            if user.id not in SUDOERS:
                _log.warning(f"Maintenance mode ON. User {user.id} (not sudoer) blocked by AdminActual for '{func_name}' in chat {chat.id}.")
                return await message.reply_text(
                    text=f"{app.mention} ɪs ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ, ᴠɪsɪᴛ <a href={SUPPORT_CHAT}>sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ</a> ғᴏʀ ᴋɴᴏᴡɪɴɢ ᴛʜᴇ ʀᴇᴀsᴏɴ.",
                    disable_web_page_preview=True,
                )

        try:
            await message.delete()
            _log.debug(f"Deleted original message {message.id} in chat {chat.id} (AdminActual).")
        except Exception as e_del:
            _log.warning(f"Failed to delete message {message.id} in chat {chat.id} (AdminActual): {e_del}")

        try:
            language = await get_lang(chat.id)
            _ = get_string(language)
        except Exception as e_lang:
            _log.error(f"Error getting language for chat {chat.id} in AdminActual: {e_lang}. Defaulting to 'en'.")
            _ = get_string("en")

        if message.sender_chat:
            _log.warning(f"Command '{func_name}' invoked by sender_chat {message.sender_chat.id} ('{message.sender_chat.title}') in chat {chat.id} (AdminActual).")
            upl = InlineKeyboardMarkup([[InlineKeyboardButton(text="ʜᴏᴡ ᴛᴏ ғɪx ?", callback_data="PROmousAdmin")]])
            return await message.reply_text(_["general_3"], reply_markup=upl)

        if user.id not in SUDOERS:
            try:
                member = await app.get_chat_member(chat.id, user.id)
                if not member.privileges or not member.privileges.can_manage_video_chats:
                    _log.warning(f"User {user.id} lacks 'can_manage_video_chats' permission for '{func_name}' in chat {chat.id}. Status: {member.status}, Privs: {member.privileges}")
                    return await message.reply_text(_["general_4"]) # "You lack permission"
            except Exception as e_perm:
                _log.error(f"Error checking 'can_manage_video_chats' for user {user.id} in chat {chat.id}: {e_perm}", exc_info=True)
                return await message.reply_text(_["general_4"]) # Default to permission denied on error
        
        _log.debug(f"AdminActual PASSED for user {user.id} running '{func_name}' in chat {chat.id}.")
        return await mystic(client, message, _) # Original function receives client, message, _

    return wrapper


def ActualAdminCB(mystic):
    """Decorator for callback queries requiring actual admin privileges or sudo."""
    async def wrapper(client, CallbackQuery):
        user = CallbackQuery.from_user
        chat = CallbackQuery.message.chat
        func_name = mystic.__name__ # Or a more descriptive name if mystic is a partial
        cb_data = CallbackQuery.data[:30] if CallbackQuery.data else "NoData" # Log first 30 chars of CB data
        _log.debug(f"ActualAdminCB decorator called for callback '{cb_data}' by user {user.id} in chat {chat.id}.")

        if await is_maintenance() is False:
            if user.id not in SUDOERS:
                _log.warning(f"Maintenance mode ON. User {user.id} (not sudoer) blocked by ActualAdminCB for callback '{cb_data}' in chat {chat.id}.")
                return await CallbackQuery.answer(
                    f"{app.mention} ɪs ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ, ᴠɪsɪᴛ sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ ғᴏʀ ᴋɴᴏᴡɪɴɢ ᴛʜᴇ ʀᴇᴀsᴏɴ.",
                    show_alert=True,
                )
        try:
            language = await get_lang(chat.id)
            _ = get_string(language)
        except Exception as e_lang:
            _log.error(f"Error getting language for chat {chat.id} in ActualAdminCB: {e_lang}. Defaulting to 'en'.")
            _ = get_string("en")

        if chat.type == ChatType.PRIVATE: # In PM, no admin checks needed beyond sudo/maintenance
            _log.debug(f"ActualAdminCB in PM for callback '{cb_data}' by user {user.id}. Skipping group admin checks.")
            return await mystic(client, CallbackQuery, _)

        is_auth_chat = await is_nonadmin_chat(chat.id) # True if /auth on
        if not is_auth_chat: # If /auth is OFF
            if user.id not in SUDOERS:
                # Check if user is an authorized user (authlist) for this chat
                # This part of logic was slightly different in original. In AdminRightsCheck, it was !is_non_admin -> check admins from adminlist.get()
                # Here, it's checking get_chat_member privileges directly for non-sudoers if auth is off.
                # It also checks get_authuser_names for an additional layer. This seems complex.
                # Sticking to the direct privilege check for ActualAdminCB first.
                try:
                    member = await app.get_chat_member(chat.id, user.id)
                    if not member.privileges or not member.privileges.can_manage_video_chats:
                        # If no direct privileges, then check authuser list as a fallback for non-sudoers
                        token = await int_to_alpha(user.id)
                        authed_users_for_chat = await get_authuser_names(chat.id) # Changed from user.id to chat.id for authuser list
                        if token not in authed_users_for_chat:
                            _log.warning(f"User {user.id} lacks 'can_manage_video_chats' and is not in authuser list for callback '{cb_data}' in chat {chat.id}.")
                            return await CallbackQuery.answer(_["general_4"], show_alert=True)
                        else:
                             _log.debug(f"User {user.id} lacks direct admin perms but is in authuser list for chat {chat.id}. Allowing callback '{cb_data}'.")
                    else:
                        _log.debug(f"User {user.id} has 'can_manage_video_chats' for callback '{cb_data}' in chat {chat.id}.")
                except Exception as e_perm_cb:
                    _log.error(f"Error checking permissions for user {user.id} in ActualAdminCB (callback '{cb_data}', chat {chat.id}): {e_perm_cb}", exc_info=True)
                    return await CallbackQuery.answer(_["general_4"], show_alert=True) # Deny on error
        
        _log.debug(f"ActualAdminCB PASSED for user {user.id} for callback '{cb_data}' in chat {chat.id}.")
        return await mystic(client, CallbackQuery, _)

    return wrapper
