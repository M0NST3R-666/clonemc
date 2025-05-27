import random
import string

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, Message, InputMediaText # Added InputMediaText
from pytgcalls.exceptions import NoActiveGroupCall

import config
from Clonify import Apple, Resso, SoundCloud, Spotify, Telegram, YouTube, app, LOGGER
from Clonify.core.call import PRO
from Clonify.utils import seconds_to_min, time_to_seconds
from Clonify.utils.channelplay import get_channeplayCB
from Clonify.utils.decorators.language import languageCB
from Clonify.utils.decorators.play import PlayWrapper
from Clonify.utils.formatters import formats
from Clonify.utils.inline import (
    botplaylist_markup,
    livestream_markup,
    playlist_markup,
    slider_markup,
    track_markup,
)
from Clonify.utils.logger import play_logs # Assuming this is a custom logger utility
from Clonify.utils.stream.stream import stream # Main streaming function
from config import BANNED_USERS, lyrical

_log = LOGGER(__name__) # Standard logger instance

@app.on_message(
   filters.command(["play", "vplay", "cplay", "cvplay", "playforce", "vplayforce", "cplayforce", "cvplayforce"] ,prefixes=["/", "!", "%", ",", "", ".", "@", "#"])
    & filters.group
    & ~BANNED_USERS
)
@PlayWrapper
async def play_commnd(
    client,
    message: Message,
    _, # Language strings
    chat_id, # Target chat_id for playback
    video, # Boolean: True if video play is requested
    channel, # String: channel name if channel play mode
    playmode, # String: "Direct" or other playmodes
    url, # String: URL if provided in command
    fplay, # Boolean: True if forceplay is requested
):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    _log.info(
        f"Play command initiated by user {user_id} ('{user_name}') in chat {message.chat.id} (target chat_id: {chat_id}). "
        f"Video: {video}, Channel: {channel}, Playmode: {playmode}, URL: {url}, ForcePlay: {fplay}"
    )

    mystic = await message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"] # "Processing..." or "Processing in channel..."
    )
    
    plist_id = None
    slider = None
    plist_type = None
    spotify = None # Flag for spotify sourced playlists/tracks
    
    audio_telegram = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )

    video_telegram = (
        (message.reply_to_message.video or message.reply_to_message.document)
        if message.reply_to_message
        else None
    )

    if audio_telegram:
        _log.info(f"Processing Telegram audio reply in chat {chat_id} by user {user_id}.")
        if audio_telegram.file_size > config.TG_AUDIO_FILESIZE_LIMIT: # Assuming this config var exists
            _log.warning(f"Telegram audio file too large: {audio_telegram.file_size} bytes in chat {chat_id}.")
            return await mystic.edit_text(_["play_5"]) # "Audio file too large"
        
        duration_min = seconds_to_min(audio_telegram.duration)
        if (audio_telegram.duration) > config.DURATION_LIMIT:
            _log.warning(f"Telegram audio duration {audio_telegram.duration}s exceeds limit in chat {chat_id}.")
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, app.mention) # "Duration limit exceeded"
            )
        
        file_path = await Telegram.get_filepath(audio=audio_telegram)
        if await Telegram.download(_, message, mystic, file_path): # Download progress in Telegram.download
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(audio_telegram, audio=True)
            dur = await Telegram.get_duration(audio_telegram, file_path) # Gets duration from downloaded file
            
            details = {"title": file_name, "link": message_link, "path": file_path, "dur": dur}
            _log.debug(f"Telegram audio details for chat {chat_id}: {details}")

            try:
                await stream(
                    _, mystic, user_id, details, chat_id, user_name, message.chat.id,
                    streamtype="telegram", forceplay=fplay
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr": err = e
                else:
                    err = _["general_2"].format(ex_type)
                    _log.error(f"Error during Telegram audio stream in chat {chat_id}: {ex_type}", exc_info=True)
                return await mystic.edit_text(str(err))
            return await mystic.delete()
        _log.warning(f"Telegram audio download failed for chat_id {chat_id}.")
        return # Download function should have replied if it failed.
    
    elif video_telegram:
        _log.info(f"Processing Telegram video/document reply in chat {chat_id} by user {user_id}.")
        if message.reply_to_message.document:
            try:
                ext = video_telegram.file_name.split(".")[-1]
                if ext.lower() not in formats:
                    _log.warning(f"Unsupported document format '{ext}' in chat {chat_id}.")
                    return await mystic.edit_text(_["play_7"].format(f"{' | '.join(formats)}"))
            except Exception as e: # No file_name or split failed
                _log.warning(f"Could not determine document extension in chat {chat_id}: {e}")
                return await mystic.edit_text(_["play_7"].format(f"{' | '.join(formats)}"))

        if video_telegram.file_size > config.TG_VIDEO_FILESIZE_LIMIT:
            _log.warning(f"Telegram video file too large: {video_telegram.file_size} bytes in chat {chat_id}.")
            return await mystic.edit_text(_["play_8"]) # "Video file too large"
        
        file_path = await Telegram.get_filepath(video=video_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(video_telegram)
            dur = await Telegram.get_duration(video_telegram, file_path)
            details = {"title": file_name, "link": message_link, "path": file_path, "dur": dur}
            _log.debug(f"Telegram video details for chat {chat_id}: {details}")

            try:
                await stream(
                    _, mystic, user_id, details, chat_id, user_name, message.chat.id,
                    video=True, streamtype="telegram", forceplay=fplay
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr": err = e
                else:
                    err = _["general_2"].format(ex_type)
                    _log.error(f"Error during Telegram video stream in chat {chat_id}: {ex_type}", exc_info=True)
                return await mystic.edit_text(str(err))
            return await mystic.delete()
        _log.warning(f"Telegram video download failed for chat_id {chat_id}.")
        return

    elif url:
        _log.info(f"Processing URL: {url} in chat {chat_id} by user {user_id}.")
        if await YouTube.exists(url):
            _log.debug(f"URL identified as YouTube: {url}")
            if "playlist" in url:
                try:
                    details = await YouTube.playlist(url, config.PLAYLIST_FETCH_LIMIT, user_id)
                except Exception as e:
                    _log.error(f"YouTube playlist fetch error for URL {url} in chat {chat_id}: {type(e).__name__} - {e}", exc_info=True)
                    return await mystic.edit_text(_["play_3"]) # "Error fetching playlist"
                streamtype = "playlist"
                plist_type = "yt"
                if "&" in url: plist_id = (url.split("=")[1]).split("&")[0]
                else: plist_id = url.split("=")[1]
                cap = _["play_10"] # Playlist caption
            else: # Single YouTube video
                try:
                    details, track_id = await YouTube.track(url) # track_id is YouTube video ID
                except Exception as e:
                    _log.error(f"YouTube track fetch error for URL {url} in chat {chat_id}: {type(e).__name__} - {e}", exc_info=True)
                    return await mystic.edit_text(_["play_3"]) # "Error fetching track"
                streamtype = "youtube"
                cap = _["play_11"].format(details["title"], details["duration_min"])
        
        elif await Spotify.valid(url):
            _log.debug(f"URL identified as Spotify: {url}")
            spotify = True
            if not config.SPOTIFY_CLIENT_ID or not config.SPOTIFY_CLIENT_SECRET:
                _log.warning("Spotify credentials not configured.")
                return await mystic.edit_text("Spotify not supported (credentials missing).")
            if "track" in url:
                try: details, track_id = await Spotify.track(url)
                except Exception as e:
                    _log.error(f"Spotify track fetch error for URL {url} in chat {chat_id}: {e}", exc_info=True)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube" # Spotify tracks are played via YouTube search
                cap = _["play_10"].format(details["title"], details["duration_min"]) # Using play_10 for track
            elif "playlist" in url:
                try: details, plist_id = await Spotify.playlist(url)
                except Exception as e:
                    _log.error(f"Spotify playlist fetch error for URL {url} in chat {chat_id}: {e}", exc_info=True)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"; plist_type = "spplay"; cap = _["play_11"].format(app.mention, user_name)
            elif "album" in url:
                try: details, plist_id = await Spotify.album(url)
                except Exception as e:
                    _log.error(f"Spotify album fetch error for URL {url} in chat {chat_id}: {e}", exc_info=True)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"; plist_type = "spalbum"; cap = _["play_11"].format(app.mention, user_name)
            elif "artist" in url:
                try: details, plist_id = await Spotify.artist(url)
                except Exception as e:
                    _log.error(f"Spotify artist fetch error for URL {url} in chat {chat_id}: {e}", exc_info=True)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"; plist_type = "spartist"; cap = _["play_11"].format(user_name)
            else:
                _log.warning(f"Invalid Spotify URL format: {url} in chat {chat_id}")
                return await mystic.edit_text(_["play_15"]) # "Invalid Spotify URL"
        
        elif await Apple.valid(url):
            _log.debug(f"URL identified as Apple Music: {url}")
            if "album" in url: # Apple Music tracks are often under /album/
                try: details, track_id = await Apple.track(url) # Assuming track processes album URLs for single tracks
                except Exception as e:
                    _log.error(f"Apple Music track fetch error for URL {url} in chat {chat_id}: {e}", exc_info=True)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"; cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                spotify = True # This seems to be a flag for "external playlist that needs track-by-track lookup"
                try: details, plist_id = await Apple.playlist(url)
                except Exception as e:
                    _log.error(f"Apple Music playlist fetch error for URL {url} in chat {chat_id}: {e}", exc_info=True)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"; plist_type = "apple"; cap = _["play_12"].format(app.mention, user_name)
            else:
                _log.warning(f"Invalid Apple Music URL format: {url} in chat {chat_id}")
                return await mystic.edit_text(_["play_3"]) # Generic error, consider specific Apple Music error string

        elif await Resso.valid(url):
            _log.debug(f"URL identified as Resso: {url}")
            try: details, track_id = await Resso.track(url)
            except Exception as e:
                _log.error(f"Resso track fetch error for URL {url} in chat {chat_id}: {e}", exc_info=True)
                return await mystic.edit_text(_["play_3"])
            streamtype = "youtube"; cap = _["play_10"].format(details["title"], details["duration_min"])

        elif await SoundCloud.valid(url):
            _log.debug(f"URL identified as SoundCloud: {url}")
            try: details, track_path = await SoundCloud.download(url) # Downloads directly
            except Exception as e:
                _log.error(f"SoundCloud download/fetch error for URL {url} in chat {chat_id}: {e}", exc_info=True)
                return await mystic.edit_text(_["play_3"])
            
            duration_sec = details["duration_sec"]
            if duration_sec > config.DURATION_LIMIT:
                _log.warning(f"SoundCloud track duration {duration_sec}s exceeds limit in chat {chat_id}.")
                return await mystic.edit_text(_["play_6"].format(config.DURATION_LIMIT_MIN,app.mention))
            try:
                await stream(
                    _, mystic, user_id, details, chat_id, user_name, message.chat.id,
                    streamtype="soundcloud", forceplay=fplay
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr": err = e
                else:
                    err = _["general_2"].format(ex_type)
                    _log.error(f"Error during SoundCloud stream for {url} in chat {chat_id}: {ex_type}", exc_info=True)
                return await mystic.edit_text(str(err))
            return await mystic.delete()
        
        else: # Direct Link (M3U8 or Index Link) or unrecognized
            _log.info(f"Processing as direct link/index: {url} in chat {chat_id}.")
            try:
                # This is a temporary stream to check if VC is active, then it's left.
                # The actual stream is started by the stream() call later.
                await PRO.stream_call(url) 
                _log.debug(f"stream_call test successful for {url} in chat {chat_id}.")
            except NoActiveGroupCall:
                _log.error(f"No active group call in logger group {config.LOGGER_ID} for direct link test {url}. User chat: {chat_id}")
                await mystic.edit_text(_["black_9"]) # "Start voice chat in logger group"
                # This message below seems to be for the admin/logger group, not user chat.
                # Consider logging this to a more appropriate place if it's an admin alert.
                # await app.send_message(chat_id=config.LOGGER_ID, text=_["play_17"])
                return
            except Exception as e:
                _log.error(f"Direct link test stream_call failed for {url} in chat {chat_id}: {type(e).__name__} - {e}", exc_info=True)
                return await mystic.edit_text(_["general_2"].format(type(e).__name__)) # Generic error to user
            
            await mystic.edit_text(_["str_2"]) # "Added direct link to queue" (or similar)
            try:
                await stream(
                    _, mystic, user_id, url, chat_id, user_name, message.chat.id,
                    video=video, streamtype="index", forceplay=fplay
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr": err = e
                else:
                    err = _["general_2"].format(ex_type)
                    _log.error(f"Error during direct link stream for {url} in chat {chat_id}: {ex_type}", exc_info=True)
                return await mystic.edit_text(str(err))
            return await play_logs(message, streamtype="M3u8 or Index Link")

    else: # No URL, so it's a search query or invalid command
        if len(message.command) < 2:
            _log.debug(f"Play command by user {user_id} in chat {chat_id} without query or reply. Showing bot playlist.")
            buttons = botplaylist_markup(_)
            return await mystic.edit_text(_["play_18"], reply_markup=InlineKeyboardMarkup(buttons)) # "Choose from bot playlist"
        
        slider = True # Indicates a search result that can be navigated
        query = message.text.split(None, 1)[1]
        if "-v" in query: query = query.replace("-v", "") # Video search flag handled by PlayWrapper
        
        _log.info(f"Processing search query: '{query}' in chat {chat_id} by user {user_id}.")
        try:
            details, track_id = await YouTube.track(query) # Search on YouTube
        except Exception as e:
            _log.error(f"YouTube search error for query '{query}' in chat {chat_id}: {e}", exc_info=True)
            return await mystic.edit_text(_["play_3"]) # "Error fetching data"
        streamtype = "youtube" # Searched tracks are treated as YouTube streams
        cap = _["play_10"].format(details["title"], details["duration_min"]) # Caption for found track

    # Common logic for both URL-based (single track) and search-based plays
    if str(playmode) == "Direct":
        _log.info(f"Playmode 'Direct' for chat {chat_id}. Streaming directly.")
        if not plist_type: # Not a playlist
            if details.get("duration_min"): # Check if duration exists (might be live stream)
                duration_sec = time_to_seconds(details["duration_min"])
                if duration_sec > config.DURATION_LIMIT:
                    _log.warning(f"Track '{details['title']}' duration {duration_sec}s exceeds limit in chat {chat_id}.")
                    return await mystic.edit_text(_["play_6"].format(config.DURATION_LIMIT_MIN, app.mention))
            else: # Likely a live stream if no duration_min after YouTube.track
                _log.debug(f"Track '{details['title']}' has no duration_min, likely a live stream. Chat: {chat_id}")
                buttons = livestream_markup(_,track_id,user_id,"v" if video else "a","c" if channel else "g","f" if fplay else "d")
                return await mystic.edit_text(_["play_13"], reply_markup=InlineKeyboardMarkup(buttons)) # "Choose stream quality for live"
        try:
            await stream(
                _, mystic, user_id, details, chat_id, user_name, message.chat.id,
                video=video, streamtype=streamtype, spotify=spotify, forceplay=fplay
            )
        except Exception as e:
            ex_type = type(e).__name__
            if ex_type == "AssistantErr": err = e
            else:
                err = _["general_2"].format(ex_type)
                _log.error(f"Error during 'Direct' stream for '{details.get('title', 'N/A')}' in chat {chat_id}: {ex_type}", exc_info=True)
            return await mystic.edit_text(str(err))
        await mystic.delete()
        return await play_logs(message, streamtype=streamtype)
    else: # Playmode is not "Direct" (i.e., queue, show buttons)
        _log.info(f"Playmode '{playmode}' (Not Direct) for chat {chat_id}. Displaying options.")
        if plist_type: # It's a playlist
            ran_hash = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            lyrical[ran_hash] = plist_id # Store playlist_id for callback
            buttons = playlist_markup(_,ran_hash,user_id,plist_type,"c" if channel else "g","f" if fplay else "d")
            await mystic.delete()
            await message.reply_photo( # Playlists usually have a generic image or platform specific image
                photo=config.PLAYLIST_IMG_URL if plist_type == "yt" else config.SPOTIFY_PLAYLIST_IMG_URL if plist_type == "spplay" else config.SPOTIFY_ALBUM_IMG_URL if plist_type == "spalbum" else config.SPOTIFY_ARTIST_IMG_URL if plist_type == "spartist" else config.APPLE_IMG_URL if plist_type == "apple" else config.PLAYLIST_IMG_URL, # Provide a default
                caption=cap, # Caption determined by platform
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return await play_logs(message, streamtype=f"Playlist : {plist_type}")
        else: # Single track to be added to queue or shown with buttons
            if slider: # From a search result
                buttons = slider_markup(_,track_id,user_id,query,0,"c" if channel else "g","f" if fplay else "d")
                await mystic.delete()
                # Send photo for slider too, not just text.
                img = await YouTube.thumbnail(track_id, True) if track_id else config.YOUTUBE_IMG_URL
                await message.reply_photo(
                    photo=img,
                    caption=_["play_10"].format(details["title"].title(), details["duration_min"]),
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                return await play_logs(message, streamtype="Searched on Youtube")
            else: # From a direct URL for a single track
                buttons = track_markup(_,track_id,user_id,"c" if channel else "g","f" if fplay else "d")
                await mystic.delete()
                img = await YouTube.thumbnail(track_id, True) if track_id and streamtype=="youtube" and not spotify else config.YOUTUBE_IMG_URL # More specific image based on source
                if spotify: img = config.SPOTIFY_IMG_URL # Generic spotify image for spotify tracks
                # TODO: Add more image sources like Apple, Resso if available in config

                await message.reply_photo(
                    photo=img,
                    caption=cap,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                return await play_logs(message, streamtype="URL Searched Inline")


@app.on_callback_query(filters.regex("MusicStream") & ~BANNED_USERS)
@languageCB
async def play_music(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    vidid, user_id_cb, mode, cplay, fplay = callback_request.split("|")
    
    _log.info(
        f"MusicStream callback: vidid={vidid}, user_id={CallbackQuery.from_user.id} (cb_user_id={user_id_cb}), "
        f"mode={mode}, cplay={cplay}, fplay={fplay}, chat_id={CallbackQuery.message.chat.id}"
    )

    if CallbackQuery.from_user.id != int(user_id_cb):
        _log.warning(f"Callback user mismatch for MusicStream. Expected {user_id_cb}, got {CallbackQuery.from_user.id}.")
        try: return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except: return

    try:
        chat_id, channel = await get_channeplayCB(_, cplay, CallbackQuery)
    except Exception as e:
        _log.error(f"Error in get_channeplayCB for MusicStream callback: {e}", exc_info=True)
        return await CallbackQuery.answer("Error determining target chat.", show_alert=True)

    user_name = CallbackQuery.from_user.first_name
    try:
        await CallbackQuery.message.delete()
        await CallbackQuery.answer()
    except: pass

    mystic = await app.send_message( # Use app.send_message as original message is deleted
        chat_id=CallbackQuery.message.chat.id, 
        text=_["play_2"].format(channel) if channel else _["play_1"]
    )
    
    try:
        details, track_id = await YouTube.track(vidid, True) # True to get video details
    except Exception as e:
        _log.error(f"YouTube.track failed in MusicStream callback for vidid {vidid}: {e}", exc_info=True)
        return await mystic.edit_text(_["play_3"])

    if details.get("duration_min"):
        duration_sec = time_to_seconds(details["duration_min"])
        if duration_sec > config.DURATION_LIMIT:
            _log.warning(f"Track duration {duration_sec}s exceeds limit in MusicStream callback (vidid {vidid}).")
            return await mystic.edit_text(_["play_6"].format(config.DURATION_LIMIT_MIN, app.mention))
    else: # Likely live stream
        _log.debug(f"Track {vidid} is likely a live stream (no duration_min) in MusicStream callback.")
        buttons = livestream_markup(_,track_id,CallbackQuery.from_user.id,mode,"c" if cplay == "c" else "g","f" if fplay == "f" else "d")
        return await mystic.edit_text(_["play_13"], reply_markup=InlineKeyboardMarkup(buttons))

    video = True if mode == "v" else None
    ffplay = True if fplay == "f" else None # Force play
    
    try:
        await stream(
            _, mystic, CallbackQuery.from_user.id, details, chat_id, user_name, 
            CallbackQuery.message.chat.id, # Original chat where callback happened
            video, streamtype="youtube", forceplay=ffplay
        )
    except Exception as e:
        ex_type = type(e).__name__
        if ex_type == "AssistantErr": err = e
        else:
            err = _["general_2"].format(ex_type)
            _log.error(f"Error during stream in MusicStream callback for vidid {vidid}: {ex_type}", exc_info=True)
        return await mystic.edit_text(str(err))
    return await mystic.delete()


@app.on_callback_query(filters.regex("ZEOmousAdmin") & ~BANNED_USERS)
async def anonymous_check_cb(client, CallbackQuery): # Renamed for clarity
    _log.debug(f"AnonymousAdmin check callback by user {CallbackQuery.from_user.id} in chat {CallbackQuery.message.chat.id}")
    try:
        await CallbackQuery.answer(
            "» ʀᴇᴠᴇʀᴛ ʙᴀᴄᴋ ᴛᴏ ᴜsᴇʀ ᴀᴄᴄᴏᴜɴᴛ :\n\nᴏᴘᴇɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ sᴇᴛᴛɪɴɢs.\n-> ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs\n-> ᴄʟɪᴄᴋ ᴏɴ ʏᴏᴜʀ ɴᴀᴍᴇ\n-> ᴜɴᴄʜᴇᴄᴋ ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴs.",
            show_alert=True,
        )
    except Exception as e:
        _log.warning(f"Error answering AnonymousAdmin callback: {e}")


@app.on_callback_query(filters.regex("ZEOPlaylists") & ~BANNED_USERS)
@languageCB
async def play_playlists_command(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    videoid_hash, user_id_cb, ptype, mode, cplay, fplay = callback_request.split("|")

    _log.info(
        f"ZEOPlaylists callback: hash={videoid_hash}, ptype={ptype}, user_id={CallbackQuery.from_user.id} (cb_user_id={user_id_cb}), "
        f"mode={mode}, cplay={cplay}, fplay={fplay}, chat_id={CallbackQuery.message.chat.id}"
    )

    if CallbackQuery.from_user.id != int(user_id_cb):
        _log.warning(f"Callback user mismatch for ZEOPlaylists. Expected {user_id_cb}, got {CallbackQuery.from_user.id}.")
        try: return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except: return

    try:
        chat_id, channel = await get_channeplayCB(_, cplay, CallbackQuery)
    except Exception as e:
        _log.error(f"Error in get_channeplayCB for ZEOPlaylists callback: {e}", exc_info=True)
        return await CallbackQuery.answer("Error determining target chat.", show_alert=True)
        
    user_name = CallbackQuery.from_user.first_name
    await CallbackQuery.message.delete()
    try: await CallbackQuery.answer()
    except: pass

    mystic = await app.send_message( # Use app.send_message
        chat_id=CallbackQuery.message.chat.id,
        text=_["play_2"].format(channel) if channel else _["play_1"]
    )
    
    original_playlist_id = lyrical.get(videoid_hash)
    if not original_playlist_id:
        _log.error(f"Playlist ID not found in lyrical cache for hash {videoid_hash}. Callback from user {user_id_cb}.")
        return await mystic.edit_text(_["play_expired_playlist"] if "play_expired_playlist" in _ else "Playlist link expired or invalid.")

    video = True if mode == "v" else None
    ffplay = True if fplay == "f" else None
    spotify_playlist_flag = False # Default, true for spotify/apple
    result = None # To store fetched playlist items

    platform_name = "Unknown"
    try:
        if ptype == "yt":
            platform_name = "YouTube"
            spotify_playlist_flag = False
            result = await YouTube.playlist(original_playlist_id, config.PLAYLIST_FETCH_LIMIT, CallbackQuery.from_user.id, True)
        elif ptype == "spplay":
            platform_name = "Spotify Playlist"
            spotify_playlist_flag = True; result, _ = await Spotify.playlist(original_playlist_id)
        elif ptype == "spalbum":
            platform_name = "Spotify Album"
            spotify_playlist_flag = True; result, _ = await Spotify.album(original_playlist_id)
        elif ptype == "spartist":
            platform_name = "Spotify Artist"
            spotify_playlist_flag = True; result, _ = await Spotify.artist(original_playlist_id)
        elif ptype == "apple":
            platform_name = "Apple Music Playlist"
            spotify_playlist_flag = True; result, _ = await Apple.playlist(original_playlist_id, True)
        else:
            _log.error(f"Unknown playlist type '{ptype}' in ZEOPlaylists callback for hash {videoid_hash}.")
            return await mystic.edit_text("Unknown playlist type.")
        
        _log.debug(f"Fetched {len(result) if result else 0} items from {platform_name} playlist {original_playlist_id} for chat {chat_id}.")

    except Exception as e:
        _log.error(f"Error fetching {platform_name} playlist {original_playlist_id} in ZEOPlaylists callback: {e}", exc_info=True)
        return await mystic.edit_text(_["play_3"]) # "Error fetching data"

    if not result:
        _log.warning(f"No tracks found after fetching {platform_name} playlist {original_playlist_id} for chat {chat_id}.")
        return await mystic.edit_text(_["play_no_tracks_in_playlist"] if "play_no_tracks_in_playlist" in _ else "No tracks found in the playlist.")

    try:
        await stream(
            _, mystic, CallbackQuery.from_user.id, result, chat_id, user_name, 
            CallbackQuery.message.chat.id, video, streamtype="playlist", 
            spotify=spotify_playlist_flag, forceplay=ffplay
        )
    except Exception as e:
        ex_type = type(e).__name__
        if ex_type == "AssistantErr": err = e
        else:
            err = _["general_2"].format(ex_type)
            _log.error(f"Error during stream in ZEOPlaylists for {platform_name} playlist {original_playlist_id}: {ex_type}", exc_info=True)
        return await mystic.edit_text(str(err))
    return await mystic.delete()


@app.on_callback_query(filters.regex("slider") & ~BANNED_USERS)
@languageCB
async def slider_queries(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    what, rtype, query, user_id_cb, cplay, fplay = callback_request.split("|")

    _log.debug(
        f"Slider callback: what={what}, rtype={rtype}, query={query}, user_id={CallbackQuery.from_user.id} (cb_user_id={user_id_cb}), "
        f"cplay={cplay}, fplay={fplay}, chat_id={CallbackQuery.message.chat.id}"
    )

    if CallbackQuery.from_user.id != int(user_id_cb):
        _log.warning(f"Callback user mismatch for slider. Expected {user_id_cb}, got {CallbackQuery.from_user.id}.")
        try: return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except: return
            
    what = str(what)
    rtype = int(rtype)
    
    new_query_type = 0
    if what == "F": # Forward
        new_query_type = 0 if rtype == 9 else int(rtype + 1)
    elif what == "B": # Backward
        new_query_type = 9 if rtype == 0 else int(rtype - 1)
    else:
        _log.warning(f"Unknown 'what' parameter in slider callback: {what}")
        return await CallbackQuery.answer("Invalid action.", show_alert=True)

    try: await CallbackQuery.answer(_["playcb_2"]) # "Fetching next/prev..."
    except: pass
            
    try:
        # Assuming YouTube.slider fetches one track based on query and new_query_type (index)
        title, duration_min, _, vidid = await YouTube.slider(query, new_query_type) 
    except Exception as e:
        _log.error(f"YouTube.slider failed in slider callback for query '{query}', type {new_query_type}: {e}", exc_info=True)
        # Might want to inform the user the slider failed or disable buttons
        return await CallbackQuery.answer("Error fetching search results.", show_alert=True)

    buttons = slider_markup(_, vidid, user_id_cb, query, new_query_type, cplay, fplay)
    
    try:
        # Original used InputMediaPhoto, but image URL was static.
        # If using dynamic images, ensure get_thumb or similar is used.
        # For simplicity and to match original fix for "photo same", text is used.
        # If a specific image per slider item is desired, this needs adjustment.
        # img = await YouTube.thumbnail(vidid, True) # Example if dynamic image needed
        # med = InputMediaPhoto(media=img, caption=_["play_10"].format(title.title(), duration_min))
        
        med = InputMediaText( # Using InputMediaText as per original code's intent to fix "photo same" issue
            text=_["play_10"].format(title.title(), duration_min),
        )
        await CallbackQuery.edit_message_media(media=med, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        _log.error(f"Failed to edit message media in slider callback: {e}", exc_info=True)
        # This can happen if the message content is identical, Pyrogram might ignore it.
        # Or if the message was deleted, etc.
        # Silently pass if it's a common "message not modified" error, or log verbosely.
        if "MessageNotModified" not in str(e): # Avoid spamming logs for this common case
             _log.warning(f"Full error editing slider message media: {type(e).__name__} - {e}", exc_info=True)
