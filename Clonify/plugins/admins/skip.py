from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, Message

import config
from Clonify import YouTube, app, LOGGER # Added LOGGER
from Clonify.core.call import PRO
from Clonify.misc import db
from Clonify.utils.database import get_loop, _clear_db_single # Assuming a function to clear a single item might exist or be useful
from Clonify.utils.decorators import AdminRightsCheck
from Clonify.utils.inline import close_markup, stream_markup
from Clonify.utils.stream.autoclear import auto_clean
from Clonify.utils.thumbnails import get_thumb
from config import BANNED_USERS

_log = LOGGER(__name__) # Added logger instance

async def play_next_track(cli, message: Message, _, chat_id, admin_user):
    """Helper function to play the next track and send notification."""
    try:
        check = db.get(chat_id)
        if not check:
            _log.info(f"Queue empty in chat {chat_id}. Stopping stream.")
            await message.reply_text(
                _["admin_6"].format(admin_user.mention, message.chat.title), # "Skipped all, VC ended"
                reply_markup=close_markup(_))
            await PRO.stop_stream(chat_id)
            return

        queued_item = check[0]
        title = (queued_item["title"]).title()
        user = queued_item["by"]
        streamtype = queued_item["streamtype"]
        videoid = queued_item["vidid"]
        file_path = queued_item["file"]
        
        _log.info(f"Attempting to play next track in chat {chat_id}: '{title}' (ID: {videoid}, Type: {streamtype})")

        db[chat_id][0]["played"] = 0 # Reset playback status
        exis = queued_item.get("old_dur") # Reset speed/seek changes
        if exis:
            db[chat_id][0]["dur"] = exis
            db[chat_id][0]["seconds"] = queued_item["old_second"]
            db[chat_id][0]["speed_path"] = None
            db[chat_id][0]["speed"] = 1.0

        status = True if str(streamtype) == "video" else None
        final_link_for_stream = None
        mystic_msg_for_dl = None

        if "live_" in file_path:
            n, final_link_for_stream = await YouTube.video(videoid, True)
            if n == 0:
                _log.error(f"Failed to get YouTube live stream URL for {videoid} in chat {chat_id}.")
                await message.reply_text(_["admin_7"].format(title)) # "Error fetching stream"
                check.pop(0) # Remove faulty track
                await auto_clean(queued_item)
                return await play_next_track(cli, message, _, chat_id, admin_user) # Try next
        elif "vid_" in file_path:
            mystic_msg_for_dl = await message.reply_text(_["call_7"], disable_web_page_preview=True) # "Downloading..."
            try:
                temp_file_path, _ = await YouTube.download(videoid, mystic_msg_for_dl, videoid=True, video=status)
                final_link_for_stream = temp_file_path
            except Exception as e_dl:
                _log.error(f"Download failed for {videoid} in chat {chat_id}: {type(e_dl).__name__} - {e_dl}")
                await mystic_msg_for_dl.edit_text(_["call_6"]) # "Error processing track"
                check.pop(0) # Remove faulty track
                await auto_clean(queued_item)
                return await play_next_track(cli, message, _, chat_id, admin_user) # Try next
            finally:
                if mystic_msg_for_dl: await mystic_msg_for_dl.delete()
        else: # index_, direct http, or local file
            final_link_for_stream = file_path

        if not final_link_for_stream:
            _log.error(f"final_link_for_stream is None for {videoid} in chat {chat_id}. Skipping.")
            check.pop(0)
            await auto_clean(queued_item)
            return await play_next_track(cli, message, _, chat_id, admin_user)

        await PRO.skip_stream(chat_id, final_link_for_stream, video=status) # skip_stream in PRO handles change_stream
        _log.info(f"PRO.skip_stream called for chat {chat_id} with: {final_link_for_stream[:100]}")
        
        img = await get_thumb(videoid)
        button = stream_markup(_, chat_id) # Ensure chat_id is what stream_markup expects
        
        # Determine markup type (tg or stream)
        markup_type = "stream"
        if videoid in ["telegram", "soundcloud"] or "index_" in file_path:
            markup_type = "tg"
            # Special handling for photo based on type (as in original)
            if videoid == "telegram":
                img = config.TELEGRAM_AUDIO_URL if str(streamtype) == "audio" else config.TELEGRAM_VIDEO_URL
            elif videoid == "soundcloud": # Assuming soundcloud only audio, or needs specific video image
                 img = config.SOUNCLOUD_IMG_URL 
            elif "index_" in file_path:
                 img = config.STREAM_IMG_URL


        caption_text = _["stream_1"].format(
            f"https://t.me/{app.username}?start=info_{videoid}", # Link for info
            title[:23],
            queued_item["dur"],
            user
        )
        if markup_type == "tg" and videoid in ["telegram", "soundcloud"]: # Different caption for these
             caption_text = _["stream_1"].format(config.SUPPORT_CHAT, title[:23], queued_item["dur"], user)
        elif "index_" in file_path: # Index stream caption
             caption_text = _["stream_2"].format(user)


        run = await message.reply_photo(
            photo=img,
            caption=caption_text,
            reply_markup=InlineKeyboardMarkup(button),
        )
        if db.get(chat_id) and db[chat_id][0]['vidid'] == videoid : # ensure the current playing is what we set
             db[chat_id][0]["mystic"] = run
             db[chat_id][0]["markup"] = markup_type
        else:
            _log.warning(f"Race condition or queue changed rapidly in chat {chat_id}. Mystic message for {videoid} might be orphaned.")


    except IndexError: # Should mean queue became empty
        _log.info(f"Queue became empty (IndexError) during play_next_track for chat {chat_id}.")
        await message.reply_text(_["admin_6"].format(admin_user.mention, message.chat.title), reply_markup=close_markup(_))
        await PRO.stop_stream(chat_id)
    except Exception as e:
        _log.exception(f"Major error in play_next_track for chat {chat_id}:")
        await message.reply_text(_["call_6"]) # Generic error message


@app.on_message(
    filters.command(["skip", "cskip", "next", "cnext"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def skip(cli, message: Message, _, chat_id):
    admin_user = message.from_user
    _log.info(f"Skip command received in chat {chat_id} by user {admin_user.id} ('{admin_user.first_name}'). Args: {message.text}")

    check = db.get(chat_id)
    if not check:
        _log.warning(f"Skip command in chat {chat_id}: Queue is already empty.")
        return await message.reply_text(_["queue_2"])

    loop = await get_loop(chat_id)
    if not len(message.command) < 2: # Args provided (multi-skip)
        if loop != 0:
            _log.warning(f"Skip (multi) command in chat {chat_id} aborted: Loop is enabled ({loop}).")
            return await message.reply_text(_["admin_8"])
        
        state = message.text.split(None, 1)[1].strip()
        if not state.isnumeric():
            _log.warning(f"Skip (multi) command in chat {chat_id}: Invalid state '{state}' - not numeric.")
            return await message.reply_text(_["admin_9"]) # "Please provide numeric value"
        
        state = int(state)
        if state <= 0 :
            _log.warning(f"Skip (multi) command in chat {chat_id}: Invalid skip count {state}.")
            return await message.reply_text(_["admin_9"])

        count = len(check)
        if state > (count -1) and count > 1 : # Cannot skip more than (songs_in_queue - 1)
             _log.warning(f"Skip (multi) command in chat {chat_id}: Invalid skip count {state} for queue size {count}.")
             # "You want to skip {state} tracks, but only {count-1} are skippable."
             return await message.reply_text(_["admin_11"].format(count - 1 if count > 0 else 0))
        if count == 1 and state >=1: # Cannot skip if only one song
            _log.warning(f"Skip (multi) command in chat {chat_id}: Cannot skip {state}, only 1 song in queue.")
            return await message.reply_text(_["admin_10"]) # "Not enough songs to skip"


        _log.info(f"Attempting to multi-skip {state} tracks in chat {chat_id}.")
        for i in range(state):
            popped_item = check.pop(0)
            await auto_clean(popped_item)
            _log.debug(f"Multi-skip: cleaned popped track {i+1}/{state}: {popped_item.get('title', 'N/A')} in chat {chat_id}")
        
        # After popping 'state' items, if 'check' is empty, stop_stream will be called by play_next_track
        _log.info(f"Successfully popped {state} tracks for multi-skip in chat {chat_id}.")

    else: # Single skip
        if loop != 0: # For single skip, if loop is on, we just replay the current song.
            _log.info(f"Single skip in chat {chat_id} with loop ON. Replaying current track.")
            # No pop, play_next_track will replay current from db[chat_id][0] after PRO.skip_stream
            pass # Let it proceed to play_next_track which will use the current track due to loop
        else:
            popped_item = check.pop(0)
            await auto_clean(popped_item)
            _log.debug(f"Single skip: cleaned popped track: {popped_item.get('title', 'N/A')} in chat {chat_id}")
            if not check: # Queue became empty
                _log.info(f"Queue emptied by single skip in chat {chat_id}. Stopping stream.")
                await message.reply_text(
                    _["admin_6"].format(admin_user.mention, message.chat.title),
                    reply_markup=close_markup(_))
                await PRO.stop_stream(chat_id)
                return
    
    # Common handler for playing the next track
    await play_next_track(cli, message, _, chat_id, admin_user)
