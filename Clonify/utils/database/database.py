import random
from typing import Dict, List, Union # Ensure Union is here

from Clonify import userbot, LOGGER 
from Clonify.core.mongo import mongodb, pymongodb 

_log = LOGGER(__name__) 

# MongoDB collections 
authdb = mongodb.adminauth
authuserdb = mongodb.authuser
autoenddb = mongodb.autoend
assdb = mongodb.assistants
blacklist_chatdb = mongodb.blacklistChat
blockeddb = mongodb.blockedusers
chatsdb = mongodb.chats
channeldb = mongodb.cplaymode # This is the collection for cmode
countdb = mongodb.upcount
gbansdb = mongodb.gban
langdb = mongodb.language
onoffdb = mongodb.onoffper 
playmodedb = mongodb.playmode
playtypedb = mongodb.playtypedb
skipdb = mongodb.skipmode
sudoersdb = mongodb.sudoers
usersdb = mongodb.tgusersdb 
privatedb = mongodb.privatechats
suggdb = mongodb.suggestion 
cleandb = mongodb.cleanmode 
queriesdb = mongodb.queries 
userdb = mongodb.userstats 
videodb = mongodb.vipvideocalls 
chatsdbc = mongodb.chatsc  
usersdbc = mongodb.tgusersdbc  

# In-memory caches/stores
active = []  
activevideo = []  
assistantdict = {}  
autoend = {}  
count = {}  
channelconnect = {} # Cache for cmode (chat_id -> connected_channel_id)
langm = {}  
loop = {}  
maintenance = []  
nonadmin = {}  
pause = {}  
playmode = {}  
playtype = {}  
skipmode = {}  
privatechats = {} 
cleanmode = [] 
suggestion = {} 
mute = {} 
audio = {} 
video = {} 


# --- Query Count --- 
_GLOBAL_QUERY_COUNTER_ID = 98324 

async def get_queries() -> int:
    _log.debug(f"Fetching global query count from DB (doc ID: {_GLOBAL_QUERY_COUNTER_ID}).")
    try:
        mode = await queriesdb.find_one({"chat_id": _GLOBAL_QUERY_COUNTER_ID})
        if not mode or "mode" not in mode:
            _log.info("Global query count not found in DB. Returning 0.")
            return 0
        _log.debug(f"Global query count retrieved: {mode['mode']}.")
        return mode["mode"]
    except Exception as e:
        _log.error(f"DB error fetching global query count: {e}", exc_info=True)
        return 0 

async def set_queries(increment_by: int = 1): 
    _log.debug(f"Incrementing global query count in DB by {increment_by} (doc ID: {_GLOBAL_QUERY_COUNTER_ID}).")
    try:
        result = await queriesdb.update_one(
            {"chat_id": _GLOBAL_QUERY_COUNTER_ID},
            {"$inc": {"mode": increment_by}},
            upsert=True,
        )
        _log.info(f"Global query count updated. Matched: {result.matched_count}, Modified: {result.modified_count}, UpsertedId: {result.upserted_id}")
    except Exception as e:
        _log.error(f"DB error incrementing global query count: {e}", exc_info=True)

# --- User Stats ---
async def get_userss(user_id: int) -> Dict[str, int]: 
    _log.debug(f"Fetching all video stats for user {user_id}.")
    try:
        stats_doc = await userdb.find_one({"chat_id": user_id}) 
        if not stats_doc or "vidid" not in stats_doc:
            _log.debug(f"No video stats found for user {user_id}.")
            return {}
        return stats_doc["vidid"] 
    except Exception as e:
        _log.error(f"DB error fetching video stats for user {user_id}: {e}", exc_info=True)
        return {}

async def get_user_top(user_id: int, video_id: str) -> Union[bool, dict]: 
    _log.debug(f"Fetching top video stats for user {user_id}, video ID {video_id}.")
    all_stats = await get_userss(user_id) 
    if video_id in all_stats:
        _log.debug(f"Found stats for user {user_id}, video ID {video_id}: {all_stats[video_id]}")
        return all_stats[video_id] 
    _log.debug(f"No stats found for user {user_id}, video ID {video_id}.")
    return False 

async def update_user_top(user_id: int, video_id: str, video_stats: dict): 
    _log.info(f"Updating video stats for user {user_id}, video ID {video_id} with data: {video_stats}.")
    try:
        all_stats = await get_userss(user_id)
        all_stats[video_id] = video_stats 
        await userdb.update_one({"chat_id": user_id}, {"$set": {"vidid": all_stats}}, upsert=True)
        _log.info(f"Successfully updated video stats for user {user_id}, video ID {video_id}.")
    except Exception as e:
        _log.error(f"DB error updating video stats for user {user_id}, video ID {video_id}: {e}", exc_info=True)

async def get_topp_users() -> dict: 
    _log.debug("Calculating top users based on total play counts from userstats DB.")
    results = {}
    try:
        async for user_stat_doc in userdb.find({"chat_id": {"$gt": 0}}): 
            user_id = user_stat_doc["chat_id"]
            total_plays = 0
            if "vidid" in user_stat_doc and isinstance(user_stat_doc["vidid"], dict):
                for video_id, stats_data in user_stat_doc["vidid"].items():
                    if isinstance(stats_data, dict) and "spot" in stats_data:
                        counts_ = stats_data["spot"]
                        if isinstance(counts_, int) and counts_ > 0:
                            total_plays += counts_
            results[user_id] = total_plays
        _log.info(f"Calculated total play counts for {len(results)} users.")
    except Exception as e:
        _log.error(f"DB error calculating top users: {e}", exc_info=True)
    return results

# --- Assistant Management ---
async def get_assistant_number(chat_id: int) -> Union[str, None]:
    assistant = assistantdict.get(chat_id)
    _log.debug(f"Cache lookup for assistant in chat {chat_id}: {'Found ' + str(assistant) if assistant else 'Not found'}")
    return assistant

async def get_client(assistant: int):
    _log.debug(f"Getting client for assistant number: {assistant}")
    clients = {1: userbot.one, 2: userbot.two, 3: userbot.three, 4: userbot.four, 5: userbot.five}
    client_instance = clients.get(int(assistant))
    if not client_instance:
        _log.error(f"Invalid assistant number requested: {assistant}. No client instance found.")
    return client_instance

async def set_assistant_new(chat_id: int, number: int):
    _log.info(f"Setting new assistant for chat {chat_id} to number {number}.")
    try:
        await assdb.update_one({"chat_id": chat_id}, {"$set": {"assistant": int(number)}}, upsert=True)
        assistantdict[chat_id] = int(number)
        _log.info(f"Successfully set assistant for chat {chat_id} to {number} in DB and cache.")
    except Exception as e:
        _log.error(f"DB error setting new assistant for chat {chat_id} to {number}: {e}", exc_info=True)

async def _set_random_assistant_db(chat_id: int, reason: str): 
    from Clonify.core.userbot import assistants 
    if not assistants:
        _log.error(f"Cannot set random assistant for chat {chat_id} ({reason}): No assistants available/configured.")
        return None, None 

    ran_assistant_num = random.choice(assistants)
    assistantdict[chat_id] = ran_assistant_num
    try:
        await assdb.update_one({"chat_id": chat_id}, {"$set": {"assistant": ran_assistant_num}}, upsert=True)
        _log.info(f"Randomly set assistant for chat {chat_id} to {ran_assistant_num} due to {reason}. Updated DB and cache.")
    except Exception as e:
        _log.error(f"DB error setting random assistant {ran_assistant_num} for chat {chat_id} ({reason}): {e}", exc_info=True)
    
    userbot_instance = await get_client(ran_assistant_num)
    return userbot_instance, ran_assistant_num

async def get_assistant(chat_id: int): 
    _log.debug(f"Getting assistant for chat {chat_id}...")
    from Clonify.core.userbot import assistants
    if not assistants:
        _log.error(f"Cannot get assistant for chat {chat_id}: No assistants available/configured.")
        return None 

    cached_assistant_num = assistantdict.get(chat_id)

    if cached_assistant_num and cached_assistant_num in assistants:
        _log.debug(f"Cache hit: Assistant {cached_assistant_num} for chat {chat_id}.")
        return await get_client(cached_assistant_num)
    
    _log.debug(f"Cache miss or invalid cached assistant for chat {chat_id}. Querying DB.")
    db_assistant_doc = await assdb.find_one({"chat_id": chat_id})

    if db_assistant_doc and db_assistant_doc.get("assistant") in assistants:
        db_assistant_num = db_assistant_doc["assistant"]
        assistantdict[chat_id] = db_assistant_num 
        _log.info(f"DB hit: Found assistant {db_assistant_num} for chat {chat_id}. Updated cache.")
        return await get_client(db_assistant_num)
    else:
        reason = "no DB record" if not db_assistant_doc else f"DB assistant {db_assistant_doc.get('assistant')} not in available list {assistants}"
        _log.info(f"No valid assistant in DB for chat {chat_id} ({reason}). Setting a new random one.")
        userbot_instance, _ = await _set_random_assistant_db(chat_id, reason)
        return userbot_instance

async def group_assistant(self_call_instance, chat_id: int):
    _log.debug(f"Getting group_assistant (PyTgCalls instance) for chat {chat_id}...")
    from Clonify.core.userbot import assistants 
    if not assistants:
        _log.error(f"Cannot get group_assistant for chat {chat_id}: No assistants available.")
        return None

    cached_assistant_num = assistantdict.get(chat_id)
    selected_assistant_num = None

    if cached_assistant_num and cached_assistant_num in assistants:
        _log.debug(f"Cache hit for group_assistant: Assistant num {cached_assistant_num} for chat {chat_id}.")
        selected_assistant_num = cached_assistant_num
    else:
        _log.debug(f"Cache miss/invalid for group_assistant chat {chat_id}. Querying DB.")
        db_assistant_doc = await assdb.find_one({"chat_id": chat_id})
        if db_assistant_doc and db_assistant_doc.get("assistant") in assistants:
            db_assistant_num = db_assistant_doc["assistant"]
            assistantdict[chat_id] = db_assistant_num 
            selected_assistant_num = db_assistant_num
            _log.info(f"DB hit for group_assistant: num {db_assistant_num} for chat {chat_id}. Updated cache.")
        else:
            reason = "no DB record for group_assistant" if not db_assistant_doc else f"DB group_assistant num {db_assistant_doc.get('assistant')} not in available list {assistants}"
            _log.info(f"No valid group_assistant in DB for chat {chat_id} ({reason}). Setting a new random one.")
            _, selected_assistant_num = await _set_random_assistant_db(chat_id, reason)

    if selected_assistant_num:
        pytgcalls_instances = {
            1: getattr(self_call_instance, 'one', None), 2: getattr(self_call_instance, 'two', None),
            3: getattr(self_call_instance, 'three', None), 4: getattr(self_call_instance, 'four', None),
            5: getattr(self_call_instance, 'five', None)
        }
        instance = pytgcalls_instances.get(selected_assistant_num)
        if not instance:
            _log.error(f"PyTgCalls instance for assistant number {selected_assistant_num} not found in Call class. Chat: {chat_id}")
            return getattr(self_call_instance, 'one', None) 
        return instance
    else: 
        _log.error(f"Failed to determine a valid assistant number for group_assistant in chat {chat_id}. Fallback to .one")
        return getattr(self_call_instance, 'one', None)

# --- Skip Mode ---
async def is_skipmode(chat_id: int) -> bool:
    mode = skipmode.get(chat_id)
    if mode is None: 
        user_doc = await skipdb.find_one({"chat_id": chat_id})
        is_on = not bool(user_doc) 
        skipmode[chat_id] = is_on
        _log.debug(f"Skipmode for chat {chat_id}: Cache miss. DB says {'ON (immediate)' if is_on else 'OFF (vote)'}. Cache updated.")
        return is_on
    _log.debug(f"Skipmode for chat {chat_id}: Cache hit. Mode: {'ON (immediate)' if mode else 'OFF (vote)'}.")
    return mode

async def skip_on(chat_id: int): 
    _log.info(f"Turning skipmode ON for chat {chat_id} (immediate skip).")
    skipmode[chat_id] = True
    try:
        await skipdb.delete_one({"chat_id": chat_id}) 
    except Exception as e:
        _log.error(f"DB error turning skipmode ON for chat {chat_id}: {e}", exc_info=True)

async def skip_off(chat_id: int): 
    _log.info(f"Turning skipmode OFF for chat {chat_id} (vote-based skip).")
    skipmode[chat_id] = False
    try:
        await skipdb.insert_one({"chat_id": chat_id}) 
    except Exception as e:
        _log.error(f"DB error turning skipmode OFF for chat {chat_id}: {e}", exc_info=True)

# --- Auto End --- 
_DB_GLOBAL_AUTOEND_FLAG_CHAT_ID = 1234

async def is_autoend() -> bool:
    try:
        user_doc = await autoenddb.find_one({"chat_id": _DB_GLOBAL_AUTOEND_FLAG_CHAT_ID})
        is_enabled = bool(user_doc)
        _log.debug(f"Autoend global status from DB: {'Enabled' if is_enabled else 'Disabled'}.")
        return is_enabled
    except Exception as e:
        _log.error(f"DB error checking autoend status: {e}", exc_info=True)
        return False 

async def autoend_on():
    _log.info("Turning global autoend ON in DB.")
    try:
        await autoenddb.update_one({"chat_id": _DB_GLOBAL_AUTOEND_FLAG_CHAT_ID}, {"$set": {"status": True}}, upsert=True)
    except Exception as e:
        _log.error(f"DB error turning autoend ON: {e}", exc_info=True)

async def autoend_off():
    _log.info("Turning global autoend OFF in DB.")
    try:
        await autoenddb.delete_one({"chat_id": _DB_GLOBAL_AUTOEND_FLAG_CHAT_ID})
    except Exception as e:
        _log.error(f"DB error turning autoend OFF: {e}", exc_info=True)

# --- Loop --- 
async def get_loop(chat_id: int) -> int:
    lop = loop.get(chat_id, 0) 
    _log.debug(f"Loop mode for chat {chat_id}: {lop}.")
    return lop

async def set_loop(chat_id: int, mode: int):
    _log.info(f"Setting loop mode for chat {chat_id} to: {mode}.")
    loop[chat_id] = mode

# --- Playmode, Playtype ---
async def get_playmode(chat_id: int) -> str:
    default_val = "Direct"
    cached_val = playmode.get(chat_id)
    if not cached_val:
        db_doc = await playmodedb.find_one({"chat_id": chat_id})
        if not db_doc or "mode" not in db_doc:
            playmode[chat_id] = default_val
            _log.debug(f"Playmode for chat {chat_id}: Cache & DB miss. Default: '{default_val}'. Cache updated.")
            return default_val
        db_val = db_doc["mode"]
        playmode[chat_id] = db_val
        _log.debug(f"Playmode for chat {chat_id}: Cache miss. DB: '{db_val}'. Cache updated.")
        return db_val
    _log.debug(f"Playmode for chat {chat_id}: Cache hit. Value: '{cached_val}'.")
    return cached_val

async def set_playmode(chat_id: int, mode: str):
    _log.info(f"Setting playmode for chat {chat_id} to: '{mode}'.")
    playmode[chat_id] = mode
    try:
        await playmodedb.update_one({"chat_id": chat_id}, {"$set": {"mode": mode}}, upsert=True)
    except Exception as e:
        _log.error(f"DB error setting playmode for chat {chat_id} to '{mode}': {e}", exc_info=True)

async def get_playtype(chat_id: int) -> str:
    default_val = "Everyone"
    cached_val = playtype.get(chat_id)
    if not cached_val:
        db_doc = await playtypedb.find_one({"chat_id": chat_id})
        if not db_doc or "mode" not in db_doc:
            playtype[chat_id] = default_val
            _log.debug(f"Playtype for chat {chat_id}: Cache & DB miss. Default: '{default_val}'. Cache updated.")
            return default_val
        db_val = db_doc["mode"]
        playtype[chat_id] = db_val
        _log.debug(f"Playtype for chat {chat_id}: Cache miss. DB: '{db_val}'. Cache updated.")
        return db_val
    _log.debug(f"Playtype for chat {chat_id}: Cache hit. Value: '{cached_val}'.")
    return cached_val

async def set_playtype(chat_id: int, mode: str):
    _log.info(f"Setting playtype for chat {chat_id} to: '{mode}'.")
    playtype[chat_id] = mode
    try:
        await playtypedb.update_one({"chat_id": chat_id}, {"$set": {"mode": mode}}, upsert=True)
    except Exception as e:
        _log.error(f"DB error setting playtype for chat {chat_id} to '{mode}': {e}", exc_info=True)


# --- Channel Play Mode (cmode) ---
async def get_cmode(chat_id: int) -> Union[int, None]:
    '''Fetches the connected channel ID for channel play mode.'''
    _log.debug(f"Fetching channel play mode (cmode) for chat_id: {chat_id}")
    # Check cache first
    cached_channel_id = channelconnect.get(chat_id)
    if cached_channel_id is not None:
        _log.debug(f"Cmode for chat {chat_id}: Cache hit. Connected channel_id: {cached_channel_id}.")
        return cached_channel_id
        
    try:
        mode_doc = await channeldb.find_one({"chat_id": chat_id})
        if mode_doc and "channel_id" in mode_doc: # Assuming 'channel_id' stores the connected channel's ID
            channel_id = int(mode_doc["channel_id"])
            channelconnect[chat_id] = channel_id # Update cache
            _log.info(f"Cmode for chat {chat_id} is connected to channel_id: {channel_id}. Cache updated.")
            return channel_id
        else:
            # If 'mode' was used in older versions for channel_id, this provides backward compatibility.
            # However, 'channel_id' is more explicit. If 'mode' stored something else, this needs adjustment.
            if mode_doc and "mode" in mode_doc and isinstance(mode_doc["mode"], int): # Check if 'mode' field might be the channel_id
                 channel_id = mode_doc["mode"]
                 channelconnect[chat_id] = channel_id # Update cache
                 _log.info(f"Cmode for chat {chat_id} (using legacy 'mode' field) is connected to channel_id: {channel_id}. Cache updated.")
                 # Consider migrating this record to use 'channel_id' field.
                 # await channeldb.update_one({"chat_id": chat_id}, {"$set": {"channel_id": channel_id}, "$unset": {"mode": ""}})
                 return channel_id

            _log.debug(f"No channel play mode (cmode) configuration found in DB for chat_id: {chat_id}")
            return None
    except Exception as e:
        _log.error(f"DB error fetching cmode for chat_id {chat_id}: {e}", exc_info=True)
        return None

async def set_cmode(chat_id: int, channel_id: int):
    '''Sets the connected channel ID for channel play mode.'''
    _log.info(f"Setting channel play mode for chat {chat_id} to channel_id: {channel_id}")
    try:
        await channeldb.update_one(
            {"chat_id": chat_id},
            {"$set": {"channel_id": channel_id}}, # Using 'channel_id' field
            upsert=True
        )
        channelconnect[chat_id] = channel_id # Update cache
        _log.info(f"Successfully set cmode for chat {chat_id} to channel {channel_id} in DB and cache.")
    except Exception as e:
        _log.error(f"DB error setting cmode for chat {chat_id} to channel {channel_id}: {e}", exc_info=True)

async def del_cmode(chat_id: int):
    '''Deletes the channel play mode setting for a chat.'''
    _log.info(f"Deleting channel play mode for chat {chat_id}")
    try:
        result = await channeldb.delete_one({"chat_id": chat_id})
        if chat_id in channelconnect: # Remove from cache
            del channelconnect[chat_id]
            _log.debug(f"Removed cmode for chat {chat_id} from cache.")

        if result.deleted_count > 0:
            _log.info(f"Successfully deleted cmode for chat {chat_id} from DB.")
        else:
            _log.debug(f"No cmode found in DB for chat {chat_id} to delete.")
    except Exception as e:
        _log.error(f"DB error deleting cmode for chat {chat_id}: {e}", exc_info=True)


# --- Language ---
async def get_lang(chat_id: int) -> str:
    default_lang = "en"
    cached_lang = langm.get(chat_id)
    if not cached_lang:
        db_lang_doc = await langdb.find_one({"chat_id": chat_id})
        if not db_lang_doc or "lang" not in db_lang_doc:
            langm[chat_id] = default_lang 
            _log.debug(f"Language for chat {chat_id}: Cache miss, DB miss. Using default: '{default_lang}'. Cache updated.")
            return default_lang
        db_lang = db_lang_doc["lang"]
        langm[chat_id] = db_lang 
        _log.debug(f"Language for chat {chat_id}: Cache miss. DB value: '{db_lang}'. Cache updated.")
        return db_lang
    _log.debug(f"Language for chat {chat_id}: Cache hit. Value: '{cached_lang}'.")
    return cached_lang

async def set_lang(chat_id: int, lang: str):
    _log.info(f"Setting language for chat {chat_id} to: '{lang}'.")
    langm[chat_id] = lang
    try:
        await langdb.update_one({"chat_id": chat_id}, {"$set": {"lang": lang}}, upsert=True)
    except Exception as e:
        _log.error(f"DB error setting language for chat {chat_id} to '{lang}': {e}", exc_info=True)

# --- Music Playing State (Pause/Resume) --- 
async def is_music_playing(chat_id: int) -> bool:
    is_playing = pause.get(chat_id, False) 
    _log.debug(f"Music playing status for chat {chat_id}: {'Playing' if is_playing else 'Paused/Not set'}.")
    return is_playing

async def music_on(chat_id: int): 
    _log.info(f"Setting music status to ON (playing) for chat {chat_id}.")
    pause[chat_id] = True

async def music_off(chat_id: int): 
    _log.info(f"Setting music status to OFF (paused) for chat {chat_id}.")
    pause[chat_id] = False

# --- Muted status ---
async def is_muted(chat_id: int) -> bool:
    is_m = mute.get(chat_id, False) 
    _log.debug(f"Bot mute status for chat {chat_id}: {'Muted' if is_m else 'Not Muted'}.")
    return is_m

async def mute_on(chat_id: int):
    _log.info(f"Setting bot mute status to ON for chat {chat_id}.")
    mute[chat_id] = True

async def mute_off(chat_id: int):
    _log.info(f"Setting bot mute status to OFF for chat {chat_id}.")
    mute[chat_id] = False

# --- Active Chats ---
async def get_active_chats() -> list:
    _log.debug(f"Retrieving list of active voice chats. Count: {len(active)}")
    return active

async def is_active_chat(chat_id: int) -> bool:
    is_act = chat_id in active
    _log.debug(f"Checking active chat status for {chat_id}: {'Active' if is_act else 'Inactive'}.")
    return is_act

async def add_active_chat(chat_id: int):
    if chat_id not in active:
        active.append(chat_id)
        _log.info(f"Added chat {chat_id} to active voice chats list.")
    else:
        _log.debug(f"Chat {chat_id} is already in active voice chats list.")

async def remove_active_chat(chat_id: int):
    if chat_id in active:
        active.remove(chat_id)
        _log.info(f"Removed chat {chat_id} from active voice chats list.")
    else:
        _log.debug(f"Chat {chat_id} not found in active voice chats list for removal.")

# --- Active Video Chats ---
async def get_active_video_chats() -> list:
    _log.debug(f"Retrieving list of active video chats. Count: {len(activevideo)}")
    return activevideo

async def is_active_video_chat(chat_id: int) -> bool:
    is_vid_act = chat_id in activevideo
    _log.debug(f"Checking active video chat status for {chat_id}: {'Active' if is_vid_act else 'Inactive'}.")
    return is_vid_act

async def add_active_video_chat(chat_id: int):
    if chat_id not in activevideo:
        activevideo.append(chat_id)
        _log.info(f"Added chat {chat_id} to active video chats list.")
    else:
        _log.debug(f"Chat {chat_id} is already in active video chats list.")

async def remove_active_video_chat(chat_id: int):
    if chat_id in activevideo:
        activevideo.remove(chat_id)
        _log.info(f"Removed chat {chat_id} from active video chats list.")
    else:
        _log.debug(f"Chat {chat_id} not found in active video chats list for removal.")

# --- Non-Admin Chat Mode ---
async def check_nonadmin_chat(chat_id: int) -> bool: # Checks DB directly
    _log.debug(f"Checking nonadmin_chat status directly from DB for chat {chat_id}.")
    try:
        user_doc = await authdb.find_one({"chat_id": chat_id})
        return bool(user_doc)
    except Exception as e:
        _log.error(f"DB error checking nonadmin_chat for {chat_id}: {e}", exc_info=True)
        return False # Default to False (admin mode) on error

async def is_nonadmin_chat(chat_id: int) -> bool: # Uses cache
    cached_val = nonadmin.get(chat_id)
    if cached_val is None:
        is_enabled = await check_nonadmin_chat(chat_id) # DB check
        nonadmin[chat_id] = is_enabled # Update cache
        _log.debug(f"Nonadmin chat mode for {chat_id}: Cache miss. DB says {'Enabled' if is_enabled else 'Disabled'}. Cache updated.")
        return is_enabled
    _log.debug(f"Nonadmin chat mode for {chat_id}: Cache hit. Mode: {'Enabled' if cached_val else 'Disabled'}.")
    return cached_val

async def add_nonadmin_chat(chat_id: int): # Enable non-admin mode
    _log.info(f"Enabling non-admin chat mode for chat {chat_id}.")
    nonadmin[chat_id] = True
    try:
        # If record exists, it's already in non-admin mode (or this logic is inverted)
        # Original: if is_admin: return. This seems to imply authdb stores chats where *admins are NOT required*.
        # So, adding to authdb means "admins not required for this chat".
        if not await check_nonadmin_chat(chat_id): # Only insert if not already in DB
            await authdb.insert_one({"chat_id": chat_id})
            _log.info(f"Non-admin mode enabled for chat {chat_id} in DB.")
        else:
            _log.debug(f"Non-admin mode was already enabled in DB for chat {chat_id}.")
    except Exception as e:
        _log.error(f"DB error enabling non-admin mode for chat {chat_id}: {e}", exc_info=True)

async def remove_nonadmin_chat(chat_id: int): # Disable non-admin mode (require admins)
    _log.info(f"Disabling non-admin chat mode for chat {chat_id} (admins required).")
    nonadmin[chat_id] = False
    try:
        if await check_nonadmin_chat(chat_id): # Only delete if currently in DB
            await authdb.delete_one({"chat_id": chat_id})
            _log.info(f"Non-admin mode disabled for chat {chat_id} in DB (record deleted).")
        else:
            _log.debug(f"Non-admin mode was already disabled in DB for chat {chat_id} (no record found).")
    except Exception as e:
        _log.error(f"DB error disabling non-admin mode for chat {chat_id}: {e}", exc_info=True)

# --- Global On/Off Switches (using onoffdb) ---
async def is_on_off(on_off_id: int) -> bool: # on_off_id is the identifier for the switch
    _log.debug(f"Checking global switch ID {on_off_id} status from DB.")
    try:
        doc = await onoffdb.find_one({"on_off": on_off_id})
        is_on = bool(doc) # If document exists, switch is considered ON
        _log.debug(f"Global switch ID {on_off_id} is {'ON' if is_on else 'OFF'}.")
        return is_on
    except Exception as e:
        _log.error(f"DB error checking global switch ID {on_off_id}: {e}", exc_info=True)
        return False # Default to OFF on error

async def add_on(on_off_id: int): # Turn a global switch ON
    _log.info(f"Turning global switch ID {on_off_id} ON.")
    try:
        if not await is_on_off(on_off_id): # Check if not already ON
            await onoffdb.insert_one({"on_off": on_off_id, "status": True}) # Add "status" for clarity
            _log.info(f"Global switch ID {on_off_id} turned ON in DB.")
        else:
            _log.debug(f"Global switch ID {on_off_id} was already ON.")
    except Exception as e:
        _log.error(f"DB error turning global switch ID {on_off_id} ON: {e}", exc_info=True)

async def add_off(on_off_id: int): # Turn a global switch OFF
    _log.info(f"Turning global switch ID {on_off_id} OFF.")
    try:
        if await is_on_off(on_off_id): # Check if currently ON
            await onoffdb.delete_one({"on_off": on_off_id})
            _log.info(f"Global switch ID {on_off_id} turned OFF in DB (record deleted).")
        else:
            _log.debug(f"Global switch ID {on_off_id} was already OFF.")
    except Exception as e:
        _log.error(f"DB error turning global switch ID {on_off_id} OFF: {e}", exc_info=True)


# --- Maintenance Mode --- (Already logged via is_maintenance, maintenance_on, maintenance_off)

# --- Served Users/Chats --- (Already logged)

async def delete_served_chat(chat_id: int): # Added this function
    _log.info(f"Deleting served chat record for chat_id: {chat_id}")
    try:
        result = await chatsdb.delete_one({"chat_id": chat_id})
        if result.deleted_count > 0:
            _log.info(f"Successfully deleted served chat record for chat_id: {chat_id}.")
        else:
            _log.debug(f"No served chat record found for chat_id: {chat_id} to delete.")
    except Exception as e:
        _log.error(f"DB error deleting served chat {chat_id}: {e}", exc_info=True)

# --- Blacklist Chats ---
async def blacklisted_chats() -> list:
    _log.debug("Fetching all blacklisted chat IDs from DB.")
    chats_list = []
    try:
        async for chat_doc in blacklist_chatdb.find({"chat_id": {"$lt": 0}}): # Assuming chat_id is negative for groups/channels
            chats_list.append(chat_doc["chat_id"])
        _log.info(f"Retrieved {len(chats_list)} blacklisted chat IDs.")
    except Exception as e:
        _log.error(f"DB error fetching blacklisted chats: {e}", exc_info=True)
    return chats_list

async def blacklist_chat(chat_id: int) -> bool:
    _log.info(f"Adding chat {chat_id} to blacklist.")
    try:
        if not await blacklist_chatdb.find_one({"chat_id": chat_id}):
            await blacklist_chatdb.insert_one({"chat_id": chat_id})
            _log.info(f"Chat {chat_id} successfully blacklisted.")
            return True
        else:
            _log.debug(f"Chat {chat_id} is already blacklisted.")
            return False # Or True, depending on desired return value semantics (already blacklisted vs newly blacklisted)
    except Exception as e:
        _log.error(f"DB error blacklisting chat {chat_id}: {e}", exc_info=True)
        return False

async def whitelist_chat(chat_id: int) -> bool:
    _log.info(f"Removing chat {chat_id} from blacklist (whitelisting).")
    try:
        result = await blacklist_chatdb.delete_one({"chat_id": chat_id})
        if result.deleted_count > 0:
            _log.info(f"Chat {chat_id} successfully whitelisted (removed from blacklist).")
            return True
        else:
            _log.debug(f"Chat {chat_id} was not found in blacklist to whitelist.")
            return False # Not found, so effectively whitelisted or never blacklisted
    except Exception as e:
        _log.error(f"DB error whitelisting chat {chat_id}: {e}", exc_info=True)
        return False

# --- Auth Users (for /auth command per chat) ---
async def _get_authusers(chat_id: int) -> Dict[str, dict]: # Renamed for clarity, internal use
    _log.debug(f"Fetching all auth users' data for chat {chat_id} from DB.")
    try:
        auth_doc = await authuserdb.find_one({"chat_id": chat_id})
        if not auth_doc or "notes" not in auth_doc: # 'notes' stores the dict of auth users
            _log.debug(f"No auth users document or 'notes' field found for chat {chat_id}.")
            return {}
        return auth_doc["notes"]
    except Exception as e:
        _log.error(f"DB error fetching auth users for chat {chat_id}: {e}", exc_info=True)
        return {}

async def get_authuser_names(chat_id: int) -> List[str]:
    _log.debug(f"Fetching auth user names for chat {chat_id}.")
    # This returns list of "names" which are tokens/keys in the 'notes' dict
    auth_users_data = await _get_authusers(chat_id)
    names_list = list(auth_users_data.keys())
    _log.debug(f"Found {len(names_list)} auth user names/tokens for chat {chat_id}.")
    return names_list

async def get_authuser(chat_id: int, name_token: str) -> Union[bool, dict]: # name is the token
    _log.debug(f"Fetching specific auth user data for chat {chat_id} with name/token: {name_token[:10]}...")
    auth_users_data = await _get_authusers(chat_id)
    if name_token in auth_users_data:
        _log.debug(f"Auth user data found for chat {chat_id}, token {name_token[:10]}.")
        return auth_users_data[name_token]
    _log.debug(f"No auth user data found for chat {chat_id}, token {name_token[:10]}.")
    return False

async def save_authuser(chat_id: int, name_token: str, user_auth_data: dict):
    _log.info(f"Saving auth user data for chat {chat_id}, token {name_token[:10]}...")
    try:
        current_auth_users = await _get_authusers(chat_id)
        current_auth_users[name_token] = user_auth_data
        await authuserdb.update_one(
            {"chat_id": chat_id}, {"$set": {"notes": current_auth_users}}, upsert=True
        )
        _log.info(f"Successfully saved auth user data for chat {chat_id}, token {name_token[:10]}.")
    except Exception as e:
        _log.error(f"DB error saving auth user for chat {chat_id}, token {name_token[:10]}: {e}", exc_info=True)

async def delete_authuser(chat_id: int, name_token: str) -> bool:
    _log.info(f"Deleting auth user data for chat {chat_id}, token {name_token[:10]}...")
    try:
        current_auth_users = await _get_authusers(chat_id)
        if name_token in current_auth_users:
            del current_auth_users[name_token]
            await authuserdb.update_one(
                {"chat_id": chat_id}, {"$set": {"notes": current_auth_users}}, upsert=True 
                # Upsert might not be ideal if notes becomes empty, could delete doc instead.
                # Or use $unset: {["notes." + name_token]: ""} if MongoDB version supports it well.
            )
            _log.info(f"Successfully deleted auth user data for chat {chat_id}, token {name_token[:10]}.")
            return True
        else:
            _log.debug(f"Auth user token {name_token[:10]} not found in chat {chat_id} for deletion.")
            return False
    except Exception as e:
        _log.error(f"DB error deleting auth user for chat {chat_id}, token {name_token[:10]}: {e}", exc_info=True)
        return False

# --- Global Bans (GBans) ---
async def get_gbanned() -> list: # Returns list of user_ids
    _log.debug("Fetching all globally banned user IDs from DB.")
    results = []
    try:
        async for user_doc in gbansdb.find({"user_id": {"$gt": 0}}):
            results.append(user_doc["user_id"])
        _log.info(f"Retrieved {len(results)} globally banned user IDs.")
    except Exception as e:
        _log.error(f"DB error fetching gbanned users: {e}", exc_info=True)
    return results

async def is_gbanned_user(user_id: int) -> bool:
    _log.debug(f"Checking if user {user_id} is globally banned.")
    try:
        user_doc = await gbansdb.find_one({"user_id": user_id})
        is_gbanned = bool(user_doc)
        _log.debug(f"User {user_id} gban status: {is_gbanned}.")
        return is_gbanned
    except Exception as e:
        _log.error(f"DB error checking gban status for user {user_id}: {e}", exc_info=True)
        return False # Assume not gbanned on error

async def add_gban_user(user_id: int):
    _log.info(f"Adding user {user_id} to global ban list.")
    try:
        if not await is_gbanned_user(user_id): # Avoid duplicates
            await gbansdb.insert_one({"user_id": user_id})
            _log.info(f"User {user_id} successfully globally banned.")
        else:
            _log.debug(f"User {user_id} is already globally banned.")
    except Exception as e:
        _log.error(f"DB error adding gban for user {user_id}: {e}", exc_info=True)

async def remove_gban_user(user_id: int):
    _log.info(f"Removing user {user_id} from global ban list.")
    try:
        result = await gbansdb.delete_one({"user_id": user_id})
        if result.deleted_count > 0:
            _log.info(f"User {user_id} successfully removed from global ban list.")
        else:
            _log.debug(f"User {user_id} not found in global ban list for removal.")
    except Exception as e:
        _log.error(f"DB error removing gban for user {user_id}: {e}", exc_info=True)

# --- Sudoers --- (Already logged in Clonify/utils/database.py, ensure consistency)

# --- Banned Users (Per-bot local bans) ---
async def get_banned_users() -> list: # Returns list of user_ids
    _log.debug("Fetching all locally banned user IDs from DB.")
    results = []
    try:
        async for user_doc in blockeddb.find({"user_id": {"$gt": 0}}):
            results.append(user_doc["user_id"])
        _log.info(f"Retrieved {len(results)} locally banned user IDs.")
    except Exception as e:
        _log.error(f"DB error fetching locally banned users: {e}", exc_info=True)
    return results

async def get_banned_count() -> int:
    _log.debug("Counting locally banned users from DB.")
    try:
        # count_documents is more efficient than fetching all then len()
        count = await blockeddb.count_documents({"user_id": {"$gt": 0}})
        _log.info(f"Found {count} locally banned users.")
        return count
    except Exception as e:
        _log.error(f"DB error counting locally banned users: {e}", exc_info=True)
        return 0

async def is_banned_user(user_id: int) -> bool:
    _log.debug(f"Checking if user {user_id} is locally banned.")
    try:
        user_doc = await blockeddb.find_one({"user_id": user_id})
        is_banned = bool(user_doc)
        _log.debug(f"User {user_id} local ban status: {is_banned}.")
        return is_banned
    except Exception as e:
        _log.error(f"DB error checking local ban status for user {user_id}: {e}", exc_info=True)
        return False # Assume not banned on error

async def add_banned_user(user_id: int):
    _log.info(f"Adding user {user_id} to local ban list.")
    try:
        if not await is_banned_user(user_id): # Avoid duplicates
            await blockeddb.insert_one({"user_id": user_id})
            _log.info(f"User {user_id} successfully locally banned.")
        else:
            _log.debug(f"User {user_id} is already locally banned.")
    except Exception as e:
        _log.error(f"DB error adding local ban for user {user_id}: {e}", exc_info=True)

async def remove_banned_user(user_id: int):
    _log.info(f"Removing user {user_id} from local ban list.")
    try:
        result = await blockeddb.delete_one({"user_id": user_id})
        if result.deleted_count > 0:
            _log.info(f"User {user_id} successfully removed from local ban list.")
        else:
            _log.debug(f"User {user_id} not found in local ban list for removal.")
    except Exception as e:
        _log.error(f"DB error removing local ban for user {user_id}: {e}", exc_info=True)

# --- Private Served Chats ---
async def get_private_served_chats() -> list:
    _log.debug("Fetching all private served chats from DB.")
    chats_list = []
    try:
        # Assuming private chat_ids are positive, unlike group/channel IDs
        async for chat_doc in privatedb.find({"chat_id": {"$gt": 0}}): 
            chats_list.append(chat_doc) # Contains the whole document
        _log.info(f"Retrieved {len(chats_list)} private served chats.")
    except Exception as e:
        _log.error(f"DB error fetching private served chats: {e}", exc_info=True)
    return chats_list

async def is_served_private_chat(chat_id: int) -> bool:
    _log.debug(f"Checking if private chat {chat_id} is served.")
    try:
        chat_doc = await privatedb.find_one({"chat_id": chat_id})
        is_served = bool(chat_doc)
        _log.debug(f"Private chat {chat_id} served status: {is_served}.")
        return is_served
    except Exception as e:
        _log.error(f"DB error checking served private chat {chat_id}: {e}", exc_info=True)
        return False

async def add_private_chat(chat_id: int):
    _log.info(f"Adding private chat {chat_id} to served list.")
    try:
        if not await is_served_private_chat(chat_id):
            await privatedb.insert_one({"chat_id": chat_id})
            _log.info(f"Private chat {chat_id} successfully added to served list.")
        else:
            _log.debug(f"Private chat {chat_id} is already in served list.")
    except Exception as e:
        _log.error(f"DB error adding private served chat {chat_id}: {e}", exc_info=True)

async def remove_private_chat(chat_id: int):
    _log.info(f"Removing private chat {chat_id} from served list.")
    try:
        result = await privatedb.delete_one({"chat_id": chat_id})
        if result.deleted_count > 0:
            _log.info(f"Private chat {chat_id} successfully removed from served list.")
        else:
            _log.debug(f"Private chat {chat_id} not found in served list for removal.")
    except Exception as e:
        _log.error(f"DB error removing private served chat {chat_id}: {e}", exc_info=True)

# --- Suggestion Mode ---
async def is_suggestion(chat_id: int) -> bool:
    cached_val = suggestion.get(chat_id)
    if cached_val is None: # Cache miss
        try:
            # If DB record exists, it means suggestion_off was called (OFF state)
            # If no DB record, it means suggestion_on was called or default (ON state)
            db_doc = await suggdb.find_one({"chat_id": chat_id})
            is_on = not bool(db_doc) 
            suggestion[chat_id] = is_on # Update cache
            _log.debug(f"Suggestion mode for chat {chat_id}: Cache miss. DB says {'ON' if is_on else 'OFF'}. Cache updated.")
            return is_on
        except Exception as e:
            _log.error(f"DB error checking suggestion mode for chat {chat_id}: {e}. Defaulting to ON.", exc_info=True)
            suggestion[chat_id] = True # Default to ON on error and cache it
            return True
    _log.debug(f"Suggestion mode for chat {chat_id}: Cache hit. Mode: {'ON' if cached_val else 'OFF'}.")
    return cached_val

async def suggestion_on(chat_id: int): # Enable suggestions (default state, remove DB record)
    _log.info(f"Turning suggestion mode ON for chat {chat_id}.")
    suggestion[chat_id] = True
    try:
        await suggdb.delete_one({"chat_id": chat_id}) # Deleting signifies ON
    except Exception as e:
        _log.error(f"DB error turning suggestion mode ON for chat {chat_id}: {e}", exc_info=True)

async def suggestion_off(chat_id: int): # Disable suggestions (add DB record)
    _log.info(f"Turning suggestion mode OFF for chat {chat_id}.")
    suggestion[chat_id] = False
    try:
        await suggdb.update_one({"chat_id": chat_id}, {"$set": {"disabled": True}}, upsert=True) # Add record to signify OFF
    except Exception as e:
        _log.error(f"DB error turning suggestion mode OFF for chat {chat_id}: {e}", exc_info=True)

# --- Clean Mode --- (In-memory only list 'cleanmode' stores chat_ids where it's OFF)
async def is_cleanmode_on(chat_id: int) -> bool:
    # If chat_id is in cleanmode list, it means mode is OFF. Otherwise, it's ON (default).
    is_off = chat_id in cleanmode 
    _log.debug(f"Cleanmode for chat {chat_id}: {'OFF' if is_off else 'ON (default)'}.")
    return not is_off # Returns True if ON, False if OFF

async def cleanmode_off(chat_id: int):
    if chat_id not in cleanmode:
        cleanmode.append(chat_id)
        _log.info(f"Cleanmode turned OFF for chat {chat_id} (added to exception list).")
    else:
        _log.debug(f"Cleanmode was already OFF for chat {chat_id}.")

async def cleanmode_on(chat_id: int): # Remove from exception list to turn ON
    try:
        if chat_id in cleanmode:
            cleanmode.remove(chat_id)
            _log.info(f"Cleanmode turned ON for chat {chat_id} (removed from exception list).")
        else:
            _log.debug(f"Cleanmode was already ON for chat {chat_id}.")
    except ValueError: # Should not happen if 'in' check is correct
        _log.warning(f"Tried to remove chat {chat_id} from cleanmode list, but not found (unexpected).")
        pass
    except Exception as e_clean_on: # Generic catch
        _log.error(f"Error turning cleanmode ON for chat {chat_id}: {e_clean_on}", exc_info=True)

# --- Clone Specific Served Users/Chats (already logged above) ---

# (Final check of all other minor utility functions in the file for logging needs)
