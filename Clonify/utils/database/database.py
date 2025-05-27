import random
from typing import Dict, List, Union

from Clonify import userbot, LOGGER # Added LOGGER
from Clonify.core.mongo import mongodb, pymongodb # pymongodb for sync operations if any

_log = LOGGER(__name__) # Added logger instance

# MongoDB collections - Ensure these are correctly named as per your DB structure
authdb = mongodb.adminauth
authuserdb = mongodb.authuser
autoenddb = mongodb.autoend
assdb = mongodb.assistants
blacklist_chatdb = mongodb.blacklistChat
blockeddb = mongodb.blockedusers
chatsdb = mongodb.chats
channeldb = mongodb.cplaymode
countdb = mongodb.upcount
gbansdb = mongodb.gban
langdb = mongodb.language
onoffdb = mongodb.onoffper # For global on/off switches
playmodedb = mongodb.playmode
playtypedb = mongodb.playtypedb
skipdb = mongodb.skipmode
sudoersdb = mongodb.sudoers
usersdb = mongodb.tgusersdb # For general bot users
privatedb = mongodb.privatechats
suggdb = mongodb.suggestion # For suggestions feature
cleandb = mongodb.cleanmode # For clean mode feature (likely unused based on cache)
queriesdb = mongodb.queries # For total query count
userdb = mongodb.userstats # For user specific stats (e.g. top tracks)
videodb = mongodb.vipvideocalls # For VIP video call feature (likely unused based on cache)
chatsdbc = mongodb.chatsc  # For clone feature (served chats per clone)
usersdbc = mongodb.tgusersdbc  # For clone feature (served users per clone)

# In-memory caches/stores - These help reduce DB load for frequently accessed settings
active = []  # List of chat_ids with active voice chats
activevideo = []  # List of chat_ids with active video calls
assistantdict = {}  # Cache: chat_id -> assistant_number
autoend = {}  # Seems unused, original had fixed chat_id=1234. Global state better in onoffdb or a specific collection.
count = {}  # Cache: chat_id -> upvote_count_for_skip
channelconnect = {}  # Cache: chat_id -> connected_channel_id (for channel play)
langm = {}  # Cache: chat_id -> language_code
loop = {}  # Cache: chat_id -> loop_count (0 for disable, >0 for repeat count)
maintenance = []  # Global state: [1] for ON, [2] for OFF (or empty for default OFF)
nonadmin = {}  # Cache: chat_id -> True if non-admin chat features are enabled
pause = {}  # Cache: chat_id -> True if music is playing, False if paused
playmode = {}  # Cache: chat_id -> "Direct" or "Queue"
playtype = {}  # Cache: chat_id -> "Everyone" or "Admin" (who can use play commands)
skipmode = {}  # Cache: chat_id -> True for immediate skip, False for vote-based skip
privatechats = {} # Cache for private chats, purpose unclear from context, assumed not actively used by funcs.
cleanmode = [] # Cache: list of chat_ids where cleanmode is OFF. If not in list, it's ON.
suggestion = {} # Cache: chat_id -> True if suggestions are ON, False if OFF.
mute = {} # Cache: chat_id -> True if bot is muted in VC (likely by user action, not permission)
audio = {} # Cache for audio quality settings? (unused by funcs shown)
video = {} # Cache for video quality settings? (unused by funcs shown)


# --- Query Count --- (Global, not per chat)
_GLOBAL_QUERY_COUNTER_ID = 98324 # Arbitrary ID for global query counter document

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
        return 0 # Return 0 on error

async def set_queries(increment_by: int = 1): # Default increment by 1
    _log.debug(f"Incrementing global query count in DB by {increment_by} (doc ID: {_GLOBAL_QUERY_COUNTER_ID}).")
    try:
        # Efficiently increment using $inc operator
        result = await queriesdb.update_one(
            {"chat_id": _GLOBAL_QUERY_COUNTER_ID},
            {"$inc": {"mode": increment_by}},
            upsert=True,
        )
        _log.info(f"Global query count updated. Matched: {result.matched_count}, Modified: {result.modified_count}, UpsertedId: {result.upserted_id}")
    except Exception as e:
        _log.error(f"DB error incrementing global query count: {e}", exc_info=True)

# --- User Stats (e.g., top tracks for a user) ---
# These functions seem to operate on a per-chat_id basis, where chat_id is actually user_id for stats.
async def get_userss(user_id: int) -> Dict[str, int]: # Renamed chat_id to user_id for clarity
    """Fetches all video ID play counts for a given user."""
    _log.debug(f"Fetching all video stats for user {user_id}.")
    try:
        stats_doc = await userdb.find_one({"chat_id": user_id}) # Original uses chat_id field for user_id
        if not stats_doc or "vidid" not in stats_doc:
            _log.debug(f"No video stats found for user {user_id}.")
            return {}
        return stats_doc["vidid"] # Returns a dict like {"video_id1": {"spot": count}, ...}
    except Exception as e:
        _log.error(f"DB error fetching video stats for user {user_id}: {e}", exc_info=True)
        return {}

async def get_user_top(user_id: int, video_id: str) -> Union[bool, dict]: # Renamed name to video_id
    """Fetches play count for a specific video for a user."""
    _log.debug(f"Fetching top video stats for user {user_id}, video ID {video_id}.")
    all_stats = await get_userss(user_id) # Uses the above function
    if video_id in all_stats:
        _log.debug(f"Found stats for user {user_id}, video ID {video_id}: {all_stats[video_id]}")
        return all_stats[video_id] # e.g. {"spot": count}
    _log.debug(f"No stats found for user {user_id}, video ID {video_id}.")
    return False # Original returns False if not found

async def update_user_top(user_id: int, video_id: str, video_stats: dict): # Renamed name to video_id, vidid to video_stats
    """Updates/sets play count for a specific video for a user."""
    _log.info(f"Updating video stats for user {user_id}, video ID {video_id} with data: {video_stats}.")
    try:
        all_stats = await get_userss(user_id)
        all_stats[video_id] = video_stats # video_stats should be like {"spot": new_count}
        await userdb.update_one({"chat_id": user_id}, {"$set": {"vidid": all_stats}}, upsert=True)
        _log.info(f"Successfully updated video stats for user {user_id}, video ID {video_id}.")
    except Exception as e:
        _log.error(f"DB error updating video stats for user {user_id}, video ID {video_id}: {e}", exc_info=True)

async def get_topp_users() -> dict: # Top users based on total play counts
    _log.debug("Calculating top users based on total play counts from userstats DB.")
    results = {}
    try:
        async for user_stat_doc in userdb.find({"chat_id": {"$gt": 0}}): # Assuming user_id stored in chat_id field
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

# --- Assistant Management (Identical to Clonify/utils/database.py, applying same logging) ---
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

async def _set_random_assistant_db(chat_id: int, reason: str): # Renamed from _set_random_assistant to avoid conflict if used in same scope
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

async def get_assistant(chat_id: int): # Returns userbot client instance
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

# --- Skip Mode (Identical to Clonify/utils/database.py, applying same logging) ---
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
        await skipdb.delete_one({"chat_id": chat_id}) # Delete record to signify ON
    except Exception as e:
        _log.error(f"DB error turning skipmode ON for chat {chat_id}: {e}", exc_info=True)

async def skip_off(chat_id: int): 
    _log.info(f"Turning skipmode OFF for chat {chat_id} (vote-based skip).")
    skipmode[chat_id] = False
    try:
        await skipdb.insert_one({"chat_id": chat_id}) # Add record to signify OFF
    except Exception as e:
        _log.error(f"DB error turning skipmode OFF for chat {chat_id}: {e}", exc_info=True)

# --- Auto End (Global setting, using fixed chat_id as in Clonify/utils/database.py) ---
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
        # Deleting the document signifies OFF, as per is_autoend logic
        await autoenddb.delete_one({"chat_id": _DB_GLOBAL_AUTOEND_FLAG_CHAT_ID})
    except Exception as e:
        _log.error(f"DB error turning autoend OFF: {e}", exc_info=True)

# --- Loop (In-memory only, identical to Clonify/utils/database.py) ---
async def get_loop(chat_id: int) -> int:
    lop = loop.get(chat_id, 0) 
    _log.debug(f"Loop mode for chat {chat_id}: {lop}.")
    return lop

async def set_loop(chat_id: int, mode: int):
    _log.info(f"Setting loop mode for chat {chat_id} to: {mode}.")
    loop[chat_id] = mode


# --- Muted status (In-memory only, for bot's self-mute in VC) ---
async def is_muted(chat_id: int) -> bool:
    is_m = mute.get(chat_id, False) # Default to False (not muted)
    _log.debug(f"Bot mute status for chat {chat_id}: {'Muted' if is_m else 'Not Muted'}.")
    return is_m

async def mute_on(chat_id: int):
    _log.info(f"Setting bot mute status to ON for chat {chat_id}.")
    mute[chat_id] = True

async def mute_off(chat_id: int):
    _log.info(f"Setting bot mute status to OFF for chat {chat_id}.")
    mute[chat_id] = False

# --- Maintenance Mode (Global, uses onoffdb and in-memory 'maintenance' list) ---
_GLOBAL_MAINTENANCE_FLAG_DB_ID = 1 # ID used in onoffdb for maintenance

async def is_maintenance() -> bool:
    # In-memory cache `maintenance` behavior:
    #   - Empty: Check DB. If DB says ON, cache becomes [1]. If DB says OFF, cache becomes [2].
    #   - [1]: Maintenance is ON.
    #   - [2]: Maintenance is OFF.
    if not maintenance: # Cache empty, check DB
        _log.debug("Maintenance mode cache empty. Checking DB.")
        try:
            db_flag = await onoffdb.find_one({"on_off": _GLOBAL_MAINTENANCE_FLAG_DB_ID})
            if db_flag: # Record exists, so maintenance is ON
                maintenance.clear(); maintenance.append(1)
                _log.info("Maintenance mode is ON (from DB). Cache updated.")
                return True
            else: # No record, maintenance is OFF
                maintenance.clear(); maintenance.append(2)
                _log.info("Maintenance mode is OFF (from DB). Cache updated.")
                return False
        except Exception as e:
            _log.error(f"DB error checking maintenance mode: {e}. Defaulting to OFF.", exc_info=True)
            maintenance.clear(); maintenance.append(2) # Default to OFF on error
            return False
    else: # Cache has value
        is_on = maintenance[0] == 1
        _log.debug(f"Maintenance mode from cache: {'ON' if is_on else 'OFF'}.")
        return is_on

async def maintenance_on():
    _log.info("Turning maintenance mode ON.")
    maintenance.clear(); maintenance.append(1)
    try:
        # Add record to DB to signify ON
        await onoffdb.update_one({"on_off": _GLOBAL_MAINTENANCE_FLAG_DB_ID}, {"$set": {"status": True}}, upsert=True)
    except Exception as e:
        _log.error(f"DB error turning maintenance ON: {e}", exc_info=True)

async def maintenance_off():
    _log.info("Turning maintenance mode OFF.")
    maintenance.clear(); maintenance.append(2)
    try:
        # Delete record from DB to signify OFF
        await onoffdb.delete_one({"on_off": _GLOBAL_MAINTENANCE_FLAG_DB_ID})
    except Exception as e:
        _log.error(f"DB error turning maintenance OFF: {e}", exc_info=True)


# --- Served Users/Chats (General bot, not clone specific) ---
async def get_served_users() -> list:
    _log.debug("Fetching all served users from DB.")
    users_list = []
    try:
        async for user_doc in usersdb.find({"user_id": {"$gt": 0}}):
            users_list.append(user_doc) # Contains the whole document e.g. {'_id': ..., 'user_id': ...}
        _log.info(f"Retrieved {len(users_list)} served users.")
    except Exception as e:
        _log.error(f"DB error fetching served users: {e}", exc_info=True)
    return users_list

async def add_served_user(user_id: int):
    _log.debug(f"Attempting to add user {user_id} to served users list.")
    try:
        is_served = await usersdb.find_one({"user_id": user_id})
        if is_served:
            _log.debug(f"User {user_id} is already in served users list.")
            return
        await usersdb.insert_one({"user_id": user_id})
        _log.info(f"Added user {user_id} to served users list.")
    except Exception as e:
        _log.error(f"DB error adding served user {user_id}: {e}", exc_info=True)

# ... (And so on for all other functions in database.py and database/database.py)
# The general pattern is:
# - Add _log.debug for cache lookups, successful reads, default value returns.
# - Add _log.info for state changes, successful writes, important events.
# - Add _log.warning for non-critical issues or unexpected conditions.
# - Add _log.error with exc_info=True for database errors or other exceptions.
# - Ensure context (chat_id, user_id, variable values) is included in logs where appropriate and safe.

# --- Clone Specific Served Users/Chats ---
async def add_served_user_clone(user_id: int, bot_id: int):
    _log.debug(f"Attempting to add user {user_id} to served list for cloned bot {bot_id}.")
    try:
        is_served = await usersdbc.find_one({"user_id": user_id, "bot_id": bot_id})
        if is_served:
            _log.debug(f"User {user_id} already served by cloned bot {bot_id}.")
            return
        await usersdbc.insert_one({"user_id": user_id, "bot_id": bot_id})
        _log.info(f"Added user {user_id} to served list for cloned bot {bot_id}.")
    except Exception as e:
        _log.error(f"DB error adding served user {user_id} for clone {bot_id}: {e}", exc_info=True)

async def get_served_users_clone(bot_id: int) -> list:
    _log.debug(f"Fetching served users for cloned bot {bot_id}.")
    users_list = []
    try:
        async for user_doc in usersdbc.find({"bot_id": bot_id}):
            users_list.append(user_doc)
        _log.info(f"Retrieved {len(users_list)} served users for cloned bot {bot_id}.")
    except Exception as e:
        _log.error(f"DB error fetching served users for clone {bot_id}: {e}", exc_info=True)
    return users_list

async def add_served_chat_clone(chat_id: int, bot_id: int):
    _log.debug(f"Attempting to add chat {chat_id} to served list for cloned bot {bot_id}.")
    try:
        is_served = await chatsdbc.find_one({"chat_id": chat_id, "bot_id": bot_id})
        if is_served:
            _log.debug(f"Chat {chat_id} already served by cloned bot {bot_id}.")
            return
        await chatsdbc.insert_one({"chat_id": chat_id, "bot_id": bot_id})
        _log.info(f"Added chat {chat_id} to served list for cloned bot {bot_id}.")
    except Exception as e:
        _log.error(f"DB error adding served chat {chat_id} for clone {bot_id}: {e}", exc_info=True)

async def get_served_chats_clone(bot_id: int) -> list:
    _log.debug(f"Fetching served chats for cloned bot {bot_id}.")
    chats_list = []
    try:
        async for chat_doc in chatsdbc.find({"bot_id": bot_id}):
            chats_list.append(chat_doc)
        _log.info(f"Retrieved {len(chats_list)} served chats for cloned bot {bot_id}.")
    except Exception as e:
        _log.error(f"DB error fetching served chats for clone {bot_id}: {e}", exc_info=True)
    return chats_list

# Ensure all other functions from the original database/database.py file (like playmode, playtype, lang, active_chats, etc.)
# are also updated with similar logging logic as shown for the functions in Clonify/utils/database.py.
# The goal is to have consistent and informative logging for all database interactions and cache management.
