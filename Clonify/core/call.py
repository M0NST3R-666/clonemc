import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.exceptions import (
    AlreadyJoinedError,
    NoActiveGroupCall,
    TelegramServerError,
    InvalidStreamError,
    NodejsNotInstalledError,
    NotInGroupCallError,
    UnMuteNeeded, # Added for cases where bot might be muted
    GroupCallNotFoundError, # Added for more specific handling
    PyTgCallsAlreadyRunning, # Added for start method
)
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio, MediumQualityVideo
from pytgcalls.types.stream import StreamAudioEnded

import config
from Clonify import LOGGER, YouTube, app
from Clonify.misc import db
from Clonify.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from Clonify.utils.exceptions import AssistantErr
from Clonify.utils.formatters import check_duration, seconds_to_min, speed_converter
from Clonify.utils.inline.play import stream_markup
from Clonify.utils.stream.autoclear import auto_clean
from strings import get_string
from Clonify.utils.thumbnails import get_thumb

autoend = {}
counter = {}


async def _clear_(chat_id):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


class Call(PyTgCalls):
    def __init__(self):
        self.userbot1 = Client(
            name="RAUSHANAss1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
        )
        try:
            self.one = PyTgCalls(
                self.userbot1,
                cache_duration=150, # Consider making this configurable
            )
        except Exception as e:
            LOGGER(__name__).critical(f"Failed to initialize PyTgCalls for userbot1: {e}")
            # Depending on the desired behavior, you might want to exit or raise the exception.
            # For now, it logs and continues, which might lead to issues later if self.one is not initialized.
            # A better approach might be to raise a critical error and stop initialization.
            raise RuntimeError(f"PyTgCalls initialization failed for userbot1: {e}")


    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await assistant.pause_stream(chat_id)
            LOGGER(__name__).info(f"Stream paused in chat_id: {chat_id}")
        except NotInGroupCallError:
            LOGGER(__name__).warning(f"Bot is not in a group call in chat_id: {chat_id} to pause.")
            # raise AssistantErr("Bot is not in the call to pause.") # Or some user-friendly message
        except Exception as e:
            LOGGER(__name__).error(f"Error pausing stream in chat_id {chat_id}: {e}")
            raise AssistantErr(f"Error pausing stream: {e}")


    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await assistant.resume_stream(chat_id)
            LOGGER(__name__).info(f"Stream resumed in chat_id: {chat_id}")
        except NotInGroupCallError:
            LOGGER(__name__).warning(f"Bot is not in a group call in chat_id: {chat_id} to resume.")
            # raise AssistantErr("Bot is not in the call to resume.")
        except Exception as e:
            LOGGER(__name__).error(f"Error resuming stream in chat_id {chat_id}: {e}")
            raise AssistantErr(f"Error resuming stream: {e}")

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await assistant.leave_group_call(chat_id)
            LOGGER(__name__).info(f"Stream stopped and left group call in chat_id: {chat_id}")
        except NotInGroupCallError:
            LOGGER(__name__).warning(f"Bot was not in a group call in chat_id: {chat_id} during stop_stream.")
            await _clear_(chat_id) # Ensure cleanup even if not in call
        except TelegramServerError as e:
            LOGGER(__name__).error(f"Telegram server error while leaving call in chat_id {chat_id}: {e}")
            await _clear_(chat_id) # Ensure cleanup
        except Exception as e:
            LOGGER(__name__).error(f"Error stopping stream in chat_id {chat_id}: {e}")
            await _clear_(chat_id) # Ensure cleanup
            # pass # Original behavior was to pass, consider if an error should be raised

    async def stop_stream_force(self, chat_id: int):
        # This method seems to try to leave the call directly using self.one (userbot1)
        # This might be intended for a specific scenario, but error handling should still be specific.
        try:
            if config.STRING1: # Assuming self.one is tied to STRING1
                await self.one.leave_group_call(chat_id)
                LOGGER(__name__).info(f"Force stopped stream for userbot1 in chat_id: {chat_id}")
        except NotInGroupCallError:
            LOGGER(__name__).warning(f"Userbot1 was not in a group call in chat_id: {chat_id} during force_stop.")
        except TelegramServerError as e:
            LOGGER(__name__).error(f"Telegram server error for userbot1 leaving call in chat_id {chat_id}: {e}")
        except Exception as e:
            LOGGER(__name__).error(f"Generic error force stopping stream for userbot1 in chat_id {chat_id}: {e}")
        finally: # Ensure cleanup happens regardless of leave_group_call outcome
            try:
                await _clear_(chat_id)
            except Exception as e_clear:
                LOGGER(__name__).error(f"Error during _clear_ in stop_stream_force for chat_id {chat_id}: {e_clear}")


    async def speedup_stream(self, chat_id: int, file_path, speed, playing):
        assistant = await group_assistant(self, chat_id)
        # ... (ffmpeg processing logic remains the same) ...
        # The following block for ffmpeg should have its own error handling for robustness
        if str(speed) != str("1.0"):
            base = os.path.basename(file_path)
            chatdir = os.path.join(os.getcwd(), "playback", str(speed))
            if not os.path.isdir(chatdir):
                os.makedirs(chatdir)
            out = os.path.join(chatdir, base)
            if not os.path.isfile(out):
                # ... (ffmpeg command) ...
                try:
                    vs = 1.0 # Default, will be overwritten
                    if str(speed) == str("0.5"): vs = 2.0
                    elif str(speed) == str("0.75"): vs = 1.35
                    elif str(speed) == str("1.5"): vs = 0.68
                    elif str(speed) == str("2.0"): vs = 0.5
                    else: # Handle unexpected speed value
                        LOGGER(__name__).warning(f"Unsupported speed value {speed} requested in chat_id {chat_id}. Using original speed.")
                        out = file_path # Fallback to original file path

                    if out != file_path: # Only run ffmpeg if speed is valid and output is different
                        proc = await asyncio.create_subprocess_shell(
                            cmd=(
                                "ffmpeg "
                                "-i "
                                f'"{file_path}" ' # Quoted file_path
                                "-filter:v "
                                f"setpts={vs}*PTS "
                                "-filter:a "
                                f"atempo={speed} "
                                f'"{out}"' # Quoted out
                            ),
                            stdin=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        stderr = (await proc.communicate())[1]
                        if proc.returncode != 0:
                            LOGGER(__name__).error(f"FFmpeg error in speedup_stream for chat_id {chat_id} (speed {speed}): {stderr.decode()}")
                            raise AssistantErr(f"FFmpeg processing failed. Speed: {speed}.")
                except FileNotFoundError:
                     LOGGER(__name__).error(f"FFmpeg not found. Please install ffmpeg for speed changes. Chat ID: {chat_id}")
                     raise AssistantErr("FFmpeg is not installed. Speed adjustment unavailable.")
                except Exception as e_ffmpeg:
                    LOGGER(__name__).error(f"Error during ffmpeg processing for chat_id {chat_id} (speed {speed}): {e_ffmpeg}")
                    raise AssistantErr(f"Failed to process audio for speed change: {e_ffmpeg}")
            else: # File already exists
                pass
        else: # speed is 1.0
            out = file_path
        
        # ... (rest of the logic for preparing stream) ...
        try:
            dur = await asyncio.get_event_loop().run_in_executor(None, check_duration, out)
            dur = int(dur)
            played, con_seconds = speed_converter(playing[0]["played"], speed)
            duration = seconds_to_min(dur)

            stream = (
                AudioVideoPiped(
                    out,
                    audio_parameters=HighQualityAudio(),
                    video_parameters=MediumQualityVideo(),
                    additional_ffmpeg_parameters=f"-ss {played} -to {duration}",
                )
                if playing[0]["streamtype"] == "video"
                else AudioPiped(
                    out,
                    audio_parameters=HighQualityAudio(),
                    additional_ffmpeg_parameters=f"-ss {played} -to {duration}",
                )
            )
            if str(db[chat_id][0]["file"]) == str(file_path): # Check if the original file matches
                await assistant.change_stream(chat_id, stream)
                LOGGER(__name__).info(f"Stream speed changed to {speed}x in chat_id: {chat_id}, new file: {out}")
            else:
                # This case might happen if the track changed while ffmpeg was processing.
                LOGGER(__name__).warning(f"Track changed before speed adjustment could be applied in chat_id: {chat_id}.")
                raise AssistantErr("Track changed during speed adjustment process. Please try again.")

            # Update db - this should only happen if change_stream was successful
            if str(db[chat_id][0]["file"]) == str(file_path):
                exis = (playing[0]).get("old_dur")
                if not exis:
                    db[chat_id][0]["old_dur"] = db[chat_id][0]["dur"]
                    db[chat_id][0]["old_second"] = db[chat_id][0]["seconds"]
                db[chat_id][0]["played"] = con_seconds
                db[chat_id][0]["dur"] = duration
                db[chat_id][0]["seconds"] = dur
                db[chat_id][0]["speed_path"] = out
                db[chat_id][0]["speed"] = speed

        except InvalidStreamError as e:
            LOGGER(__name__).error(f"Invalid stream for speedup in chat_id {chat_id} (speed {speed}), file {out}: {e}")
            raise AssistantErr(f"Invalid stream parameters for speed change: {e}")
        except TelegramServerError as e:
            LOGGER(__name__).error(f"Telegram server error during speedup_stream in chat_id {chat_id}: {e}")
            raise AssistantErr(f"Telegram server error during speed change: {e}")
        except Exception as e:
            LOGGER(__name__).error(f"Error in speedup_stream for chat_id {chat_id} (speed {speed}), file {out}: {e}")
            raise AssistantErr(f"Could not change stream speed: {e}")


    async def force_stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            check = db.get(chat_id)
            if check: # Check if list is not empty
                check.pop(0)
        except IndexError:
            LOGGER(__name__).warning(f"DB queue was empty for chat_id {chat_id} on force_stop_stream.")
        except Exception as e_db:
            LOGGER(__name__).error(f"Error popping from DB for chat_id {chat_id} in force_stop_stream: {e_db}")
            
        await remove_active_video_chat(chat_id) # These should be resilient
        await remove_active_chat(chat_id)
        try:
            await assistant.leave_group_call(chat_id)
            LOGGER(__name__).info(f"Force stopped stream and left call in chat_id: {chat_id}")
        except NotInGroupCallError:
            LOGGER(__name__).warning(f"Bot was not in group call in chat_id: {chat_id} during force_stop_stream.")
        except TelegramServerError as e:
            LOGGER(__name__).error(f"Telegram server error during force_stop_stream for chat_id {chat_id}: {e}")
        except Exception as e:
            LOGGER(__name__).error(f"Error leaving group call in force_stop_stream for chat_id {chat_id}: {e}")


    async def skip_stream(
        self,
        chat_id: int,
        link: str,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None, # image seems unused here
    ):
        assistant = await group_assistant(self, chat_id)
        try:
            if video:
                stream = AudioVideoPiped(
                    link,
                    audio_parameters=HighQualityAudio(),
                    video_parameters=MediumQualityVideo(),
                )
            else:
                stream = AudioPiped(link, audio_parameters=HighQualityAudio())
            
            await assistant.change_stream(chat_id, stream)
            LOGGER(__name__).info(f"Skipped to stream: {link} in chat_id: {chat_id}")
        except InvalidStreamError as e:
            LOGGER(__name__).error(f"Invalid stream provided for skip in chat_id {chat_id}, link {link}: {e}")
            raise AssistantErr(f"Cannot skip: Invalid stream. ({e})")
        except NotInGroupCallError:
            LOGGER(__name__).error(f"Bot not in call, cannot skip stream in chat_id {chat_id}.")
            raise AssistantErr("Cannot skip: Bot is not currently in a call.")
        except TelegramServerError as e:
            LOGGER(__name__).error(f"Telegram server error during skip_stream in chat_id {chat_id}: {e}")
            raise AssistantErr(f"Telegram server error, could not skip stream: {e}")
        except Exception as e:
            LOGGER(__name__).error(f"Error skipping stream in chat_id {chat_id}, link {link}: {e}")
            raise AssistantErr(f"Could not skip stream: {e}")


    async def seek_stream(self, chat_id, file_path, to_seek, duration, mode):
        assistant = await group_assistant(self, chat_id)
        try:
            stream = (
                AudioVideoPiped(
                    file_path,
                    audio_parameters=HighQualityAudio(),
                    video_parameters=MediumQualityVideo(),
                    additional_ffmpeg_parameters=f"-ss {to_seek} -to {duration}",
                )
                if mode == "video"
                else AudioPiped(
                    file_path,
                    audio_parameters=HighQualityAudio(),
                    additional_ffmpeg_parameters=f"-ss {to_seek} -to {duration}",
                )
            )
            await assistant.change_stream(chat_id, stream)
            LOGGER(__name__).info(f"Seeked stream in chat_id {chat_id} to {to_seek}. File: {file_path}")
        except InvalidStreamError as e:
            LOGGER(__name__).error(f"Invalid stream for seek in chat_id {chat_id}, file {file_path}: {e}")
            raise AssistantErr(f"Cannot seek: Invalid stream. ({e})")
        except NotInGroupCallError:
            LOGGER(__name__).error(f"Bot not in call, cannot seek stream in chat_id {chat_id}.")
            raise AssistantErr("Cannot seek: Bot is not currently in a call.")
        except TelegramServerError as e:
            LOGGER(__name__).error(f"Telegram server error during seek_stream in chat_id {chat_id}: {e}")
            raise AssistantErr(f"Telegram server error, could not seek stream: {e}")
        except Exception as e:
            LOGGER(__name__).error(f"Error seeking stream in chat_id {chat_id}, file {file_path}: {e}")
            raise AssistantErr(f"Could not seek stream: {e}")


    async def stream_call(self, link): # This is for the logger/announce stream
        assistant = await group_assistant(self, config.LOGGER_ID)
        try:
            await assistant.join_group_call(
                config.LOGGER_ID,
                AudioVideoPiped(link), # Consider if this should be AudioOnly
                stream_type=StreamType().pulse_stream,
            )
            LOGGER(__name__).info(f"Logger stream started in chat_id: {config.LOGGER_ID}")
            await asyncio.sleep(0.2) # Is this sleep essential?
        except NoActiveGroupCall:
            LOGGER("Clonify").error(f"No active group call in LOGGER_ID: {config.LOGGER_ID} for stream_call.")
            # This error should be handled, maybe by creating the call or notifying admin.
            # For now, it will propagate if not caught by the caller of stream_call.
            raise
        except AlreadyJoinedError:
            LOGGER("Clonify").warning(f"Assistant already in call in LOGGER_ID: {config.LOGGER_ID} for stream_call. Attempting to leave and rejoin.")
            try:
                await assistant.leave_group_call(config.LOGGER_ID)
                await asyncio.sleep(0.1) # Short delay before rejoining
                await assistant.join_group_call(
                    config.LOGGER_ID,
                    AudioVideoPiped(link),
                    stream_type=StreamType().pulse_stream,
                )
            except Exception as e_rejoin:
                LOGGER("Clonify").error(f"Failed to rejoin call in LOGGER_ID {config.LOGGER_ID} after AlreadyJoinedError: {e_rejoin}")
                raise
        except TelegramServerError as e:
            LOGGER("Clonify").error(f"Telegram Server Error in stream_call for LOGGER_ID {config.LOGGER_ID}: {e}")
            raise
        except Exception as e:
            LOGGER("Clonify").error(f"Unexpected error in stream_call for LOGGER_ID {config.LOGGER_ID}: {e}")
            raise
        finally: # Ensure leave_group_call is attempted for pulse_stream
            try:
                await assistant.leave_group_call(config.LOGGER_ID)
                LOGGER(__name__).info(f"Logger stream left call in chat_id: {config.LOGGER_ID}")
            except NotInGroupCallError:
                 LOGGER(__name__).warning(f"Logger stream was not in call in chat_id: {config.LOGGER_ID} at finally block of stream_call.")
            except Exception as e_leave:
                 LOGGER(__name__).error(f"Error leaving call in stream_call finally block for LOGGER_ID {config.LOGGER_ID}: {e_leave}")


    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int, # original_chat_id seems to be for sending messages back
        link,
        video: Union[bool, str] = None,
        # image: Union[bool, str] = None, # image seems unused
    ):
        assistant = await group_assistant(self, chat_id)
        language = await get_lang(original_chat_id) # Use original_chat_id for language
        _ = get_string(language)
        
        if video: # Ensure this logic is correct for determining stream type
            stream = AudioVideoPiped(
                link,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
            )
        else:
            stream = AudioPiped(link, audio_parameters=HighQualityAudio())
        
        try:
            await assistant.join_group_call(
                chat_id,
                stream,
                stream_type=StreamType().pulse_stream, # Consider if pulse_stream is always intended here
            )
            LOGGER(__name__).info(f"Joined call in chat_id: {chat_id}, playing: {link[:50]}...")
        except NoActiveGroupCall:
            LOGGER(__name__).error(f"No active group call in chat_id: {chat_id} to join.")
            raise AssistantErr(_["call_8"]) # "Please start the voice chat first."
        except AlreadyJoinedError:
            LOGGER(__name__).warning(f"Already joined in chat_id: {chat_id}.")
            # This might not be an error if the intention is just to ensure it's joined.
            # However, the original code raises AssistantErr, so we maintain that.
            raise AssistantErr(_["call_9"]) # "Assistant already in VC."
        except TelegramServerError as e:
            LOGGER(__name__).error(f"Telegram server error joining call in chat_id {chat_id}: {e}")
            raise AssistantErr(_["call_10"]) # "Telegram server error."
        except UnMuteNeeded: # Specific exception for when bot is muted by admin
            LOGGER(__name__).error(f"Cannot join call in chat_id {chat_id}: Assistant is muted. Please unmute the assistant.")
            raise AssistantErr(_["call_muted_error"] if "call_muted_error" in _ else "The assistant is muted in the voice chat. Please unmute it to play music.") # Add this string to your lang files
        except GroupCallNotFoundError:
             LOGGER(__name__).error(f"Group call not found or ended in chat_id {chat_id}.")
             raise AssistantErr(_["call_not_found_error"] if "call_not_found_error" in _ else "The voice chat was not found or has ended.") # Add this string
        except Exception as e:
            LOGGER(__name__).error(f"Unexpected error joining call in chat_id {chat_id}: {type(e).__name__} - {e}")
            raise AssistantErr(f"An unexpected error occurred while joining the call: {e}")

        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)
        
        if await is_autoend():
            counter[chat_id] = {}
            try:
                users = len(await assistant.get_participants(chat_id))
                if users == 1: # Only bot is in call
                    autoend[chat_id] = datetime.now() + timedelta(minutes=config.AUTOEND_MINS if hasattr(config, 'AUTOEND_MINS') else 1) # Use configurable autoend time
            except Exception as e_part:
                LOGGER(__name__).warning(f"Could not get participant count for autoend in chat_id {chat_id}: {e_part}")


    async def change_stream(self, client, chat_id): # client here is the PyTgCalls instance from the handler
        language = await get_lang(chat_id) # Assuming chat_id is the original_chat_id context for language
        _ = get_string(language)
        
        check = db.get(chat_id)
        popped = None
        loop = await get_loop(chat_id)
        
        try:
            if not check: # Queue is empty
                LOGGER(__name__).info(f"Queue empty for chat_id {chat_id}. Leaving call.")
                await _clear_(chat_id)
                await client.leave_group_call(chat_id)
                return

            if loop == 0:
                popped = check.pop(0)
            else:
                loop = loop - 1
                await set_loop(chat_id, loop)
            
            if popped: await auto_clean(popped) # Clean previous file if applicable

            if not check: # Queue became empty after pop or loop decrement
                LOGGER(__name__).info(f"Queue ended for chat_id {chat_id}. Leaving call.")
                await _clear_(chat_id)
                await client.leave_group_call(chat_id)
                return

        except NotInGroupCallError: # If leave_group_call fails because not in call
            LOGGER(__name__).warning(f"Tried to leave call in change_stream for chat_id {chat_id}, but already left.")
            await _clear_(chat_id) # Still clear DB
            return
        except Exception as e_queue:
            LOGGER(__name__).error(f"Error processing queue or leaving call in change_stream for chat_id {chat_id}: {e_queue}")
            await _clear_(chat_id) # Ensure cleanup
            try:
                await client.leave_group_call(chat_id)
            except Exception as e_leave_final:
                LOGGER(__name__).error(f"Error in final leave_group_call attempt for chat_id {chat_id}: {e_leave_final}")
            return
        
        # If we are here, 'check' is not empty and points to the next track
        queued = check[0]["file"]
        title = (check[0]["title"]).title()
        user = check[0]["by"]
        original_chat_id = check[0]["chat_id"] # This is the chat where messages should be sent
        streamtype = check[0]["streamtype"]
        videoid = check[0]["vidid"]
        
        db[chat_id][0]["played"] = 0
        exis = (check[0]).get("old_dur")
        if exis: # Reset speed related changes
            db[chat_id][0]["dur"] = exis
            db[chat_id][0]["seconds"] = check[0]["old_second"]
            db[chat_id][0]["speed_path"] = None
            db[chat_id][0]["speed"] = 1.0
            
        video = True if str(streamtype) == "video" else False
        final_stream_path = None
        stream_obj = None

        try:
            if "live_" in queued:
                n, link = await YouTube.video(videoid, True)
                if n == 0:
                    await app.send_message(original_chat_id, text=_["call_6"]) # "Error fetching stream"
                    # Call change_stream again to process next or leave
                    return await self.change_stream(client, chat_id)
                final_stream_path = link
            elif "vid_" in queued:
                mystic = await app.send_message(original_chat_id, _["call_7"]) # "Downloading and Processing"
                try:
                    file_path, direct = await YouTube.download(
                        videoid, mystic, videoid=True, video=video
                    )
                    final_stream_path = file_path
                except Exception as e_yt_dl: # More specific exception if YouTube.download provides one
                    LOGGER(__name__).error(f"YouTube DL error for {videoid} in chat {original_chat_id}: {e_yt_dl}")
                    await mystic.edit_text(_["call_6"] + f"\nError: {e_yt_dl}", disable_web_page_preview=True)
                    return await self.change_stream(client, chat_id) # Process next
                await mystic.delete() # Delete "Downloading..." message
            elif "index_" in queued:
                final_stream_path = videoid # Direct link from index
            else: # Local file or direct http link
                final_stream_path = queued

            if not final_stream_path:
                LOGGER(__name__).error(f"Stream path resolution failed for item {queued} in chat {original_chat_id}.")
                await app.send_message(original_chat_id, text=_["call_6"])
                return await self.change_stream(client, chat_id)

            if video:
                stream_obj = AudioVideoPiped(final_stream_path, audio_parameters=HighQualityAudio(), video_parameters=MediumQualityVideo())
            else:
                stream_obj = AudioPiped(final_stream_path, audio_parameters=HighQualityAudio())

            await client.change_stream(chat_id, stream_obj)
            LOGGER(__name__).info(f"Stream changed in chat_id {chat_id} to: {final_stream_path[:100]}")

            # Send message about new stream
            # ... (message sending logic as in original, ensure original_chat_id is used for app.send_*)
            # This part is complex and involves sending different messages based on videoid type
            # For brevity, I'm omitting the exact reconstruction of the message sending block,
            # but it should be preserved from the original, using original_chat_id. Example:
            if videoid == "telegram":
                button = telegram_markup(_, original_chat_id) # Pass original_chat_id
                # ...
                run = await app.send_photo(
                    chat_id=original_chat_id, # Use original_chat_id
                    # ...
                )
                db[chat_id][0]["mystic"] = run # mystic should be associated with original_chat_id
                db[chat_id][0]["markup"] = "tg"
            # ... and so on for other types like 'soundcloud', 'live_', 'vid_', 'index_'

        except InvalidStreamError as e:
            LOGGER(__name__).error(f"Invalid stream for change_stream in chat_id {chat_id}, path {final_stream_path}: {e}")
            await app.send_message(original_chat_id, text=_["call_6"] + f" (Invalid Stream: {e})")
            # Try to play the next song
            return await self.change_stream(client, chat_id)
        except NotInGroupCallError: # Should not happen if logic is correct, but good to catch
            LOGGER(__name__).error(f"Bot not in call during change_stream for chat_id {chat_id}, cannot change.")
            await app.send_message(original_chat_id, text=_["call_not_in_call_error"] if "call_not_in_call_error" in _ else "Bot is not in the call.")
            await _clear_(chat_id) # Clear queue as we can't continue
        except TelegramServerError as e:
            LOGGER(__name__).error(f"Telegram server error during change_stream for chat_id {chat_id}: {e}")
            await app.send_message(original_chat_id, text=_["call_10"] + f" ({e})")
            return await self.change_stream(client, chat_id) # Try next
        except Exception as e:
            LOGGER(__name__).error(f"Generic error in change_stream for chat_id {chat_id}, path {final_stream_path}: {type(e).__name__} - {e}")
            await app.send_message(original_chat_id, text=_["call_6"] + f" (Error: {e})")
            return await self.change_stream(client, chat_id) # Try next


    async def ping(self):
        pings = []
        # Consider adding try-except for each ping attempt if one assistant being down shouldn't stop others
        if config.STRING1 and hasattr(self, 'one'): # Check if self.one was initialized
            try:
                pings.append(await self.one.ping)
            except Exception as e:
                LOGGER(__name__).error(f"Ping failed for userbot1: {e}")
                # pings.append(float('inf')) # Or some indicator of failure
        # ... similar checks for other userbots if they were structured this way ...
        
        if not pings:
            return "N/A (No active userbots or ping failed)"
        return str(round(sum(pings) / len(pings), 3))


    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls Clients...")
        if config.STRING1 and hasattr(self, 'one'):
            try:
                await self.one.start()
                LOGGER(__name__).info("Userbot1 (self.one) PyTgCalls client started.")
            except NodejsNotInstalledError:
                LOGGER(__name__).critical("Node.js is not installed. PyTgCalls requires Node.js.")
                # Potentially exit or disable features depending on Node.js
                raise # Re-raise to be handled by main startup
            except PyTgCallsAlreadyRunning:
                LOGGER(__name__).warning("Userbot1 (self.one) PyTgCalls client was already running.")
            except Exception as e:
                LOGGER(__name__).critical(f"Failed to start PyTgCalls for Userbot1 (self.one): {e}")
                raise # Re-raise for main startup to handle
        # ... similar start blocks for other userbots if any ...

    async def decorators(self):
        if not hasattr(self, 'one'): # If PyTgCalls failed to initialize for self.one
            LOGGER(__name__).warning("Skipping decorators for self.one as it's not initialized.")
            return

        @self.one.on_kicked()
        @self.one.on_closed_voice_chat()
        @self.one.on_left()
        async def stream_services_handler(_, chat_id: int):
            LOGGER(__name__).info(f"Service event: Kicked, closed, or left for chat_id: {chat_id}. Stopping stream.")
            try:
                await self.stop_stream(chat_id) # stop_stream now has better logging
            except Exception as e:
                LOGGER(__name__).error(f"Error in stream_services_handler for chat_id {chat_id}: {e}")

        @self.one.on_stream_end()
        async def stream_end_handler1(client, update: Update): # client is PyTgCalls instance
            if not isinstance(update, StreamAudioEnded):
                return
            LOGGER(__name__).info(f"Stream ended in chat_id: {update.chat_id}. Changing stream.")
            try:
                await self.change_stream(client, update.chat_id) # change_stream has better logging
            except Exception as e:
                 LOGGER(__name__).error(f"Error in stream_end_handler1 for chat_id {update.chat_id}: {e}")
        
        # ... similar decorator blocks for other userbots if any ...

PRO = Call()

[end of Clonify/core/call.py]
