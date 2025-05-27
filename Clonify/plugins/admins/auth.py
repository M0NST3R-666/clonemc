from pyrogram import filters
from pyrogram.types import Message

from Clonify import app, LOGGER # Added LOGGER
from Clonify.utils import extract_user, int_to_alpha
from Clonify.utils.database import (
    delete_authuser,
    get_authuser,
    get_authuser_names,
    save_authuser,
)
from Clonify.utils.decorators import AdminActual, language
from Clonify.utils.inline import close_markup
from config import BANNED_USERS, adminlist

_log = LOGGER(__name__) # Added logger instance

@app.on_message(filters.command("auth") & filters.group & ~BANNED_USERS)
@AdminActual
async def auth(client, message: Message, _):
    chat_id = message.chat.id
    admin_user = message.from_user
    if not message.reply_to_message:
        if len(message.command) != 2:
            _log.warning(f"Auth command misused by {admin_user.id} in chat {chat_id}: No reply and wrong arg count.")
            return await message.reply_text(_["general_1"])
    
    user_to_auth = await extract_user(message)
    if not user_to_auth:
        _log.warning(f"Auth command failed for {admin_user.id} in chat {chat_id}: Could not extract user.")
        return await message.reply_text(_["general_2"]) # Assuming general_2 is "could not extract user"

    token = await int_to_alpha(user_to_auth.id)
    _check = await get_authuser_names(chat_id)
    count = len(_check)

    if int(count) == 25:
        _log.warning(f"Auth limit reached in chat {chat_id}. Admin {admin_user.id} tried to auth {user_to_auth.id}.")
        return await message.reply_text(_["auth_1"])

    if token not in _check:
        assis = {
            "auth_user_id": user_to_auth.id,
            "auth_name": user_to_auth.first_name,
            "admin_id": admin_user.id,
            "admin_name": admin_user.first_name,
        }
        get = adminlist.get(chat_id)
        if get:
            if user_to_auth.id not in get:
                get.append(user_to_auth.id)
        
        await save_authuser(chat_id, token, assis)
        _log.info(f"User {user_to_auth.id} ('{user_to_auth.first_name}') authorized by admin {admin_user.id} ('{admin_user.first_name}') in chat {chat_id}.")
        return await message.reply_text(_["auth_2"].format(user_to_auth.mention))
    else:
        _log.info(f"User {user_to_auth.id} ('{user_to_auth.first_name}') was already authorized in chat {chat_id}. Attempt by admin {admin_user.id}.")
        return await message.reply_text(_["auth_3"].format(user_to_auth.mention))


@app.on_message(filters.command("unauth") & filters.group & ~BANNED_USERS)
@AdminActual
async def unauthusers(client, message: Message, _):
    chat_id = message.chat.id
    admin_user = message.from_user
    if not message.reply_to_message:
        if len(message.command) != 2:
            _log.warning(f"Unauth command misused by {admin_user.id} in chat {chat_id}: No reply and wrong arg count.")
            return await message.reply_text(_["general_1"])

    user_to_unauth = await extract_user(message)
    if not user_to_unauth:
        _log.warning(f"Unauth command failed for {admin_user.id} in chat {chat_id}: Could not extract user.")
        return await message.reply_text(_["general_2"])

    token = await int_to_alpha(user_to_unauth.id)
    deleted = await delete_authuser(chat_id, token)
    
    get = adminlist.get(chat_id)
    if get:
        if user_to_unauth.id in get:
            get.remove(user_to_unauth.id)

    if deleted:
        _log.info(f"User {user_to_unauth.id} ('{user_to_unauth.first_name}') unauthorized by admin {admin_user.id} ('{admin_user.first_name}') in chat {chat_id}.")
        return await message.reply_text(_["auth_4"].format(user_to_unauth.mention))
    else:
        _log.warning(f"User {user_to_unauth.id} ('{user_to_unauth.first_name}') was not found in auth list of chat {chat_id} for unauthorization. Attempt by admin {admin_user.id}.")
        return await message.reply_text(_["auth_5"].format(user_to_unauth.mention))


@app.on_message(
    filters.command(["authlist", "authusers"]) & filters.group & ~BANNED_USERS
)
@language
async def authusers(client, message: Message, _):
    chat_id = message.chat.id
    _log.info(f"Authlist requested by {message.from_user.id} in chat {chat_id}.")
    _wtf = await get_authuser_names(chat_id)
    if not _wtf:
        return await message.reply_text(_["setting_4"])
    else:
        j = 0
        mystic = await message.reply_text(_["auth_6"])
        text = _["auth_7"].format(message.chat.title)
        for umm_token in _wtf:
            _umm = await get_authuser(chat_id, umm_token)
            user_id = _umm["auth_user_id"]
            admin_id = _umm["admin_id"]
            admin_name = _umm["admin_name"]
            try:
                # Consider batching get_users if _wtf is very long, though 25 is max.
                user = (await app.get_users(user_id)).first_name
                j += 1
            except Exception as e:
                _log.warning(f"Error fetching user details for user_id {user_id} in chat {chat_id} during authlist: {type(e).__name__} - {e}")
                continue # Skip this user if details can't be fetched
            text += f"{j}➤ {user}[<code>{user_id}</code>]\n"
            text += f"   {_['auth_8']} {admin_name}[<code>{admin_id}</code>]\n\n"
        
        if j == 0: # All users failed to fetch
             _log.warning(f"Authlist for chat {chat_id} resulted in no users after fetching details.")
             return await mystic.edit_text(_["setting_4"]) # No users found or fetch failed for all

        await mystic.edit_text(text, reply_markup=close_markup(_))
