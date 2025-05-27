import time
import random
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtubesearchpython.__future__ import VideosSearch

import config
from Clonify import app, LOGGER # Added LOGGER
from Clonify.misc import _boot_
from Clonify.plugins.sudo.sudoers import sudoers_list
from Clonify.utils.database import get_served_chats, get_served_users, get_sudoers
from Clonify.utils import bot_sys_stats
from Clonify.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
    is_on_off,
)
from Clonify.utils.decorators.language import LanguageStart
from Clonify.utils.formatters import get_readable_time
from Clonify.utils.inline import help_pannel, private_panel, start_panel
from config import BANNED_USERS, STREAMI_PICS, GREET
from strings import get_string

_log = LOGGER(__name__) # Added logger instance

@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    user = message.from_user
    _log.info(f"Private start command from user {user.id} ('{user.first_name}'). Message: {message.text}")
    
    # Animated loading message
    loading_msg_text = random.choice(GREET)
    loading_1 = await message.reply_text(loading_msg_text)
    await add_served_user(user.id)
    
    animation_chars = ["ʟᴏᴀᴅɪɴɢ", "ʟᴏᴀᴅɪɴɢ.", "ʟᴏᴀᴅɪɴɢ..", "ʟᴏᴀᴅɪɴɢ..."]
    for char_anim in animation_chars:
        await loading_1.edit_text(f"<b>{char_anim}</b>")
        await asyncio.sleep(0.1)
    await loading_1.delete()

    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]
        _log.debug(f"Start command with payload: '{name}' from user {user.id}")
        if name[0:4] == "help":
            _log.info(f"User {user.id} accessed help panel via start payload.")
            keyboard = help_pannel(_)
            return await message.reply_photo(
                random.choice(STREAMI_PICS),
                caption=_["help_1"].format(config.SUPPORT_CHAT),
                reply_markup=keyboard,
            )
        if name[0:3] == "sud":
            _log.info(f"User {user.id} accessed sudoers list via start payload.")
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2) and config.LOGGER_ID: # Check if LOGGER_ID is configured
                try:
                    await app.send_message(
                        chat_id=config.LOGGER_ID,
                        text=f"✦ {user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>sᴜᴅᴏʟɪsᴛ</b>.\n\n<b>✦ ᴜsᴇʀ ɪᴅ ➠</b> <code>{user.id}</code>\n<b>✦ ᴜsᴇʀɴᴀᴍᴇ ➠</b> @{user.username if user.username else 'N/A'}",
                    )
                except Exception as e_log_send:
                    _log.error(f"Failed to send sudo check log to LOGGER_ID {config.LOGGER_ID}: {e_log_send}")
            return
        if name[0:3] == "inf":
            _log.info(f"User {user.id} checking track info via start payload: {name}")
            m = await message.reply_text("🔎")
            query = (str(name)).replace("info_", "", 1)
            youtube_query = f"https://www.youtube.com/watch?v={query}"
            try:
                results = VideosSearch(youtube_query, limit=1)
                video_results = (await results.next()).get("result")
                if not video_results or len(video_results) == 0:
                    _log.warning(f"No YouTube video found for info query: {youtube_query} by user {user.id}")
                    await m.edit_text(_["start_no_info"] if "start_no_info" in _ else "Could not find information for this track.")
                    return
                
                result = video_results[0]
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]
                
                searched_text = _["start_6"].format(title, duration, views, published, channellink, channel, app.mention)
                key = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text=_["S_B_8"], url=link),
                      InlineKeyboardButton(text=_["S_B_9"], url=config.SUPPORT_CHAT)]]
                )
                await m.delete()
                await app.send_photo(chat_id=message.chat.id, photo=thumbnail, caption=searched_text, reply_markup=key)
                
                if await is_on_off(2) and config.LOGGER_ID:
                    try:
                        await app.send_message(
                            chat_id=config.LOGGER_ID,
                            text=f"✦ {user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>ᴛʀᴀᴄᴋ ɪɴғᴏʀᴍᴀᴛɪᴏɴ</b> ({title}).\n\n✦ <b>ᴜsᴇʀ ɪᴅ ➠</b> <code>{user.id}</code>\n✦ <b>ᴜsᴇʀɴᴀᴍᴇ ➠</b> @{user.username if user.username else 'N/A'}",
                        )
                    except Exception as e_log_send:
                        _log.error(f"Failed to send track info log to LOGGER_ID {config.LOGGER_ID}: {e_log_send}")
            except Exception as e_ytsearch:
                _log.error(f"Error fetching YouTube info for query {youtube_query} by user {user.id}: {e_ytsearch}", exc_info=True)
                await m.edit_text(_["start_yt_error"] if "start_yt_error" in _ else "Error fetching video information.")
            return
    else:
        _log.info(f"User {user.id} started bot in PM without payload. Sending private panel.")
        out = private_panel(_)
        await message.reply_photo(
            random.choice(STREAMI_PICS),
            caption=_["start_2"].format(user.mention, app.mention),
            reply_markup=InlineKeyboardMarkup(out),
        )
        if await is_on_off(2) and config.LOGGER_ID:
            try:
                await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"✦ {user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n✦ <b>ᴜsᴇʀ ɪᴅ ➠</b> <code>{user.id}</code>\n✦ <b>ᴜsᴇʀɴᴀᴍᴇ ➠</b> @{user.username if user.username else 'N/A'}",
                )
            except Exception as e_log_send:
                _log.error(f"Failed to send private start log to LOGGER_ID {config.LOGGER_ID}: {e_log_send}")


@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    user = message.from_user
    chat = message.chat
    _log.info(f"Group start command from user {user.id} ('{user.first_name}') in chat {chat.id} ('{chat.title}').")
    out = start_panel(_)
    uptime = int(time.time() - _boot_)
    await message.reply_photo(
        random.choice(STREAMI_PICS),
        caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
        reply_markup=InlineKeyboardMarkup(out),
    )
    await add_served_chat(chat.id)


@app.on_message(filters.new_chat_members, group=-1) # Using group -1 to catch it early
async def welcome(client, message: Message):
    chat = message.chat
    for member in message.new_chat_members:
        _log.info(f"New member(s) detected in chat {chat.id} ('{chat.title}'). Member ID: {member.id} ('{member.first_name}').")
        try:
            language = await get_lang(chat.id)
            _ = get_string(language)
            if await is_banned_user(member.id):
                _log.warning(f"Banned user {member.id} ('{member.first_name}') tried to join chat {chat.id}. Attempting to ban again.")
                try:
                    await message.chat.ban_member(member.id)
                    _log.info(f"Successfully re-banned user {member.id} in chat {chat.id}.")
                except Exception as e_ban:
                    _log.error(f"Failed to re-ban user {member.id} in chat {chat.id}: {e_ban}", exc_info=True)
            
            if member.id == app.id: # Bot was added to a new group
                _log.info(f"Bot @{app.username} (ID: {app.id}) added to chat {chat.id} ('{chat.title}') by user {message.from_user.id if message.from_user else 'Unknown'}.")
                if chat.type != ChatType.SUPERGROUP:
                    _log.warning(f"Bot added to non-supergroup chat {chat.id} ('{chat.title}'). Leaving chat.")
                    await message.reply_text(_["start_4"]) # "Bot only works in supergroups"
                    await app.leave_chat(chat.id)
                    return
                
                if chat.id in await blacklisted_chats():
                    _log.warning(f"Bot added to blacklisted chat {chat.id} ('{chat.title}'). Leaving chat.")
                    # Message contains links, ensure disable_web_page_preview=True
                    await message.reply_text(
                        _["start_5"].format(app.mention,f"https://t.me/{app.username}?start=sudolist",config.SUPPORT_CHAT),
                        disable_web_page_preview=True,
                    )
                    await app.leave_chat(chat.id)
                    return

                _log.info(f"Bot successfully joined chat {chat.id} ('{chat.title}'). Sending welcome message.")
                out = start_panel(_)
                await message.reply_text(
                    text=_["start_3"].format(message.from_user.mention if message.from_user else "Someone", app.mention, chat.title, app.mention),
                    reply_markup=InlineKeyboardMarkup(out),
                )
                await add_served_chat(chat.id)
                # message.stop_propagation() # This might prevent other handlers, use with caution.
                                           # If no other handlers for new_chat_members for the bot itself, it's fine.
        except Exception as ex:
            # Using _log.exception for unexpected errors in the welcome handler
            _log.exception(f"Error in welcome handler for new member {member.id} in chat {chat.id}:")

# Ensure message.stop_propagation() is only called if absolutely necessary.
# If other plugins might want to act on the bot joining a group, stop_propagation() would prevent them.
# For now, assuming it's intended to stop further processing for bot's own add event.
# If a new member is NOT the bot, propagation should usually continue.
# The current logic correctly stops propagation only if member.id == app.id (which is fine).
