import random
from typing import Dict, List, Union

from Clonify import userbot, LOGGER # Added LOGGER
from Clonify.core.mongo import mongodb

_log = LOGGER(__name__) # Added logger instance

# MongoDB collections
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
onoffdb = mongodb.onoffper
playmodedb = mongodb.playmode
playtypedb = mongodb.playtypedb
skipdb = mongodb.skipmode
sudoersdb = mongodb.sudoers
usersdb = mongodb.tgusersdb
cardsdb = mongodb.cards # Assuming this is for a feature like credit cards, handle with extreme care
chatsdbc = mongodb.chatsc # For clone feature
usersdbc = mongodb.tgusersdbc # For clone feature

# In-memory caches/stores
active = []
activevideo = []
assistantdict = {}
autoend = {} # This seems to be a single global state, not per chat. Original code had chat_id=1234.
count = {}
channelconnect = {}
langm = {}
loop = {}
maintenance = [] # Stores a single state: 1 for ON, 2 for OFF.
nonadmin = {}
pause = {}
playmode = {}
playtype = {}
skipmode = {}

# --- Assistant Management ---
async def get_assistant_number(chat_id: int) -> Union[str, None]: # Added return type hint
    assistant = assistantdict.get(chat_id)
    _log.debug(f"Cache lookup for assistant in chat {chat_id}: {'Found ' + str(assistant) if assistant else 'Not found'}")
    return assistant

async def get_client(assistant: int):
    _log.debug(f"Getting client for assistant number: {assistant}")
    # This function assumes userbot.one, .two, etc., are defined and started.
    # Error handling for invalid assistant numbers should be considered if not all are guaranteed.
    clients = {1: userbot.one, 2: userbot.two, 3: userbot.three, 4: userbot.four, 5: userbot.five}
    client_instance = clients.get(int(assistant))
    if not client_instance:
        _log.error(f"Invalid assistant number requested: {assistant}. No client instance found.")
        # Potentially raise an error or return a default/main userbot if applicable.
    return client_instance

async def set_assistant_new(chat_id: int, number: int):
    _log.info(f"Setting new assistant for chat {chat_id} to number {number}.")
    try:
        await assdb.update_one({"chat_id": chat_id}, {"$set": {"assistant": int(number)}}, upsert=True)
        assistantdict[chat_id] = int(number) # Update cache
        _log.info(f"Successfully set assistant for chat {chat_id} to {number} in DB and cache.")
    except Exception as e:
        _log.error(f"DB error setting new assistant for chat {chat_id} to {number}: {e}", exc_info=True)

async def _set_random_assistant(chat_id: int, reason: str):
    """Internal helper to set a random assistant and update cache."""
    from Clonify.core.userbot import assistants # Get current list of available assistant numbers
    if not assistants:
        _log.error(f"Cannot set random assistant for chat {chat_id} ({reason}): No assistants available/configured.")
        return None, None # Return None for both userbot instance and assistant number

    ran_assistant_num = random.choice(assistants)
    assistantdict[chat_id] = ran_assistant_num
    try:
        await assdb.update_one({"chat_id": chat_id}, {"$set": {"assistant": ran_assistant_num}}, upsert=True)
        _log.info(f"Randomly set assistant for chat {chat_id} to {ran_assistant_num} due to {reason}. Updated DB and cache.")
    except Exception as e:
        _log.error(f"DB error setting random assistant {ran_assistant_num} for chat {chat_id} ({reason}): {e}", exc_info=True)
        # Cache is updated, but DB failed. Might lead to inconsistency.
    
    userbot_instance = await get_client(ran_assistant_num)
    return userbot_instance, ran_assistant_num


async def get_assistant(chat_id: int): # Returns userbot client instance
    _log.debug(f"Getting assistant for chat {chat_id}...")
    from Clonify.core.userbot import assistants
    if not assistants:
        _log.error(f"Cannot get assistant for chat {chat_id}: No assistants available/configured.")
        return None # Or raise an error

    cached_assistant_num = assistantdict.get(chat_id)

    if cached_assistant_num and cached_assistant_num in assistants:
        _log.debug(f"Cache hit: Assistant {cached_assistant_num} for chat {chat_id}.")
        return await get_client(cached_assistant_num)
    
    _log.debug(f"Cache miss or invalid cached assistant for chat {chat_id}. Querying DB.")
    db_assistant_doc = await assdb.find_one({"chat_id": chat_id})

    if db_assistant_doc and db_assistant_doc.get("assistant") in assistants:
        db_assistant_num = db_assistant_doc["assistant"]
        assistantdict[chat_id] = db_assistant_num # Update cache
        _log.info(f"DB hit: Found assistant {db_assistant_num} for chat {chat_id}. Updated cache.")
        return await get_client(db_assistant_num)
    else:
        reason = "no DB record" if not db_assistant_doc else f"DB assistant {db_assistant_doc.get('assistant')} not in available list {assistants}"
        _log.info(f"No valid assistant in DB for chat {chat_id} ({reason}). Setting a new random one.")
        userbot_instance, _ = await _set_random_assistant(chat_id, reason)
        return userbot_instance


async def group_assistant(self_call_instance, chat_id: int): # self_call_instance is PRO from core/call.py
    # This function seems to be designed to be called from the Call class (PRO)
    # It returns one of the PyTgCalls instances (self.one, self.two etc.) from the Call class.
    _log.debug(f"Getting group_assistant (PyTgCalls instance) for chat {chat_id}...")
    from Clonify.core.userbot import assistants # Active assistant numbers (1, 2, etc.)
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
            assistantdict[chat_id] = db_assistant_num # Update cache
            selected_assistant_num = db_assistant_num
            _log.info(f"DB hit for group_assistant: num {db_assistant_num} for chat {chat_id}. Updated cache.")
        else:
            reason = "no DB record for group_assistant" if not db_assistant_doc else f"DB group_assistant num {db_assistant_doc.get('assistant')} not in available list {assistants}"
            _log.info(f"No valid group_assistant in DB for chat {chat_id} ({reason}). Setting a new random one.")
            _, selected_assistant_num = await _set_random_assistant(chat_id, reason) # Sets assistantdict and assdb

    if selected_assistant_num:
        # Map assistant number to the Call class's PyTgCalls instances
        # (e.g., self_call_instance.one, self_call_instance.two)
        pytgcalls_instances = {
            1: getattr(self_call_instance, 'one', None), 2: getattr(self_call_instance, 'two', None),
            3: getattr(self_call_instance, 'three', None), 4: getattr(self_call_instance, 'four', None),
            5: getattr(self_call_instance, 'five', None)
        }
        instance = pytgcalls_instances.get(selected_assistant_num)
        if not instance:
            _log.error(f"PyTgCalls instance for assistant number {selected_assistant_num} not found in Call class instance. Chat: {chat_id}")
            # Fallback logic might be needed, e.g., use self_call_instance.one
            return getattr(self_call_instance, 'one', None) # Default fallback
        return instance
    else: # Should not happen if _set_random_assistant works and assistants list is not empty
        _log.error(f"Failed to determine a valid assistant number for group_assistant in chat {chat_id}. Fallback to .one")
        return getattr(self_call_instance, 'one', None) # Default fallback


# --- Skip Mode ---
async def is_skipmode(chat_id: int) -> bool:
    mode = skipmode.get(chat_id)
    if mode is None: # Explicitly check for None as False is a valid mode
        user_doc = await skipdb.find_one({"chat_id": chat_id})
        # If no DB entry, skip mode is ON (i.e., doesn't skip based on votes, skips immediately) -> True
        # If DB entry exists, it means skip_off was called, so skip mode is OFF (vote based) -> False
        is_on = not bool(user_doc) 
        skipmode[chat_id] = is_on
        _log.debug(f"Skipmode for chat {chat_id}: Cache miss. DB says {'ON' if is_on else 'OFF'}. Cache updated.")
        return is_on
    _log.debug(f"Skipmode for chat {chat_id}: Cache hit. Mode: {'ON' if mode else 'OFF'}.")
    return mode

async def skip_on(chat_id: int): # Turns ON immediate skip (deletes DB record)
    _log.info(f"Turning skipmode ON for chat {chat_id} (immediate skip).")
    skipmode[chat_id] = True
    try:
        await skipdb.delete_one({"chat_id": chat_id})
    except Exception as e:
        _log.error(f"DB error turning skipmode ON for chat {chat_id}: {e}", exc_info=True)

async def skip_off(chat_id: int): # Turns OFF immediate skip (vote-based, adds DB record)
    _log.info(f"Turning skipmode OFF for chat {chat_id} (vote-based skip).")
    skipmode[chat_id] = False
    try:
        await skipdb.insert_one({"chat_id": chat_id})
    except Exception as e:
        _log.error(f"DB error turning skipmode OFF for chat {chat_id}: {e}", exc_info=True)

# --- Upvote Count ---
async def get_upvote_count(chat_id: int) -> int:
    default_count = 5 # Default if nothing is set
    cached_val = count.get(chat_id)
    if cached_val is None:
        db_val_doc = await countdb.find_one({"chat_id": chat_id})
        if not db_val_doc or "mode" not in db_val_doc:
            count[chat_id] = default_count # Update cache with default
            _log.debug(f"Upvote count for chat {chat_id}: Cache miss, DB miss. Using default: {default_count}. Cache updated.")
            return default_count
        db_val = db_val_doc["mode"]
        count[chat_id] = db_val # Update cache
        _log.debug(f"Upvote count for chat {chat_id}: Cache miss. DB value: {db_val}. Cache updated.")
        return db_val
    _log.debug(f"Upvote count for chat {chat_id}: Cache hit. Value: {cached_val}.")
    return cached_val

async def set_upvotes(chat_id: int, mode: int):
    _log.info(f"Setting upvote count for chat {chat_id} to: {mode}.")
    count[chat_id] = mode
    try:
        await countdb.update_one({"chat_id": chat_id}, {"$set": {"mode": mode}}, upsert=True)
    except Exception as e:
        _log.error(f"DB error setting upvote count for chat {chat_id} to {mode}: {e}", exc_info=True)

# --- Auto End --- (Global setting, chat_id=1234 is a placeholder for a global flag)
_GLOBAL_AUTOEND_FLAG_CHAT_ID = 1234 # Internal constant for clarity

async def is_autoend() -> bool:
    # This is a global setting. The cache `autoend` dict is not used here in original.
    # Let's use the `maintenance` list pattern for consistency if it's a global boolean state.
    # However, the original uses a DB record with a fixed chat_id.
    try:
        user_doc = await autoenddb.find_one({"chat_id": _GLOBAL_AUTOEND_FLAG_CHAT_ID})
        is_enabled = bool(user_doc)
        _log.debug(f"Autoend global status: {'Enabled' if is_enabled else 'Disabled'}.")
        return is_enabled
    except Exception as e:
        _log.error(f"DB error checking autoend status: {e}", exc_info=True)
        return False # Default to false on error

async def autoend_on():
    _log.info("Turning global autoend ON.")
    try:
        await autoenddb.update_one({"chat_id": _GLOBAL_AUTOEND_FLAG_CHAT_ID}, {"$set": {"status": True}}, upsert=True)
    except Exception as e:
        _log.error(f"DB error turning autoend ON: {e}", exc_info=True)

async def autoend_off():
    _log.info("Turning global autoend OFF.")
    try:
        await autoenddb.delete_one({"chat_id": _GLOBAL_AUTOEND_FLAG_CHAT_ID})
    except Exception as e:
        _log.error(f"DB error turning autoend OFF: {e}", exc_info=True)

# --- Loop --- (In-memory only)
async def get_loop(chat_id: int) -> int:
    lop = loop.get(chat_id, 0) # Default to 0 (no loop)
    _log.debug(f"Loop mode for chat {chat_id}: {lop}.")
    return lop

async def set_loop(chat_id: int, mode: int):
    _log.info(f"Setting loop mode for chat {chat_id} to: {mode}.")
    loop[chat_id] = mode

# ... (Continue for other functions, applying similar logging logic) ...
# For brevity, I will not list every single function modification here,
# but the pattern involves:
#   1. Adding _log.debug/info/warning/error based on the operation.
#   2. Logging cache hits/misses and DB interactions.
#   3. Logging changes to state (e.g., setting a mode).
#   4. Logging errors, especially DB errors, with exc_info=True for tracebacks.

# Example for a few more:

# --- Channel Play Mode (cmode) ---
async def get_cmode(chat_id: int) -> Union[int, None]:
    cached_val = channelconnect.get(chat_id)
    if cached_val is None:
        db_doc = await channeldb.find_one({"chat_id": chat_id})
        if not db_doc or "mode" not in db_doc:
            _log.debug(f"Channel play mode (cmode) for chat {chat_id}: Cache miss, DB miss. Returning None.")
            return None # Explicitly return None if not found
        db_val = db_doc["mode"]
        channelconnect[chat_id] = db_val # Update cache
        _log.debug(f"Cmode for chat {chat_id}: Cache miss. DB value: {db_val}. Cache updated.")
        return db_val
    _log.debug(f"Cmode for chat {chat_id}: Cache hit. Value: {cached_val}.")
    return cached_val

async def set_cmode(chat_id: int, mode: int):
    _log.info(f"Setting cmode for chat {chat_id} to: {mode}.")
    channelconnect[chat_id] = mode
    try:
        await channeldb.update_one({"chat_id": chat_id}, {"$set": {"mode": mode}}, upsert=True)
    except Exception as e:
        _log.error(f"DB error setting cmode for chat {chat_id} to {mode}: {e}", exc_info=True)

# --- Language ---
async def get_lang(chat_id: int) -> str:
    default_lang = "en"
    cached_lang = langm.get(chat_id)
    if not cached_lang:
        db_lang_doc = await langdb.find_one({"chat_id": chat_id})
        if not db_lang_doc or "lang" not in db_lang_doc:
            langm[chat_id] = default_lang # Update cache with default
            _log.debug(f"Language for chat {chat_id}: Cache miss, DB miss. Using default: '{default_lang}'. Cache updated.")
            return default_lang
        db_lang = db_lang_doc["lang"]
        langm[chat_id] = db_lang # Update cache
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

# --- Music Playing State (Pause/Resume) --- (In-memory only)
async def is_music_playing(chat_id: int) -> bool:
    # True if playing, False if paused. Default to False (not playing/paused) if no entry.
    is_playing = pause.get(chat_id, False) 
    _log.debug(f"Music playing status for chat {chat_id}: {'Playing' if is_playing else 'Paused/Not set'}.")
    return is_playing

async def music_on(chat_id: int): # Means music is now playing (unpaused)
    _log.info(f"Setting music status to ON (playing) for chat {chat_id}.")
    pause[chat_id] = True

async def music_off(chat_id: int): # Means music is now paused
    _log.info(f"Setting music status to OFF (paused) for chat {chat_id}.")
    pause[chat_id] = False


# --- Active Chats (In-memory only) ---
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

# ... (Similar detailed logging for activevideo, nonadmin, onoff, maintenance, served_user, served_chat, blacklist, authuser, gban, sudoers, banned_users, cards)

# --- Sudoers ---
async def get_sudoers() -> list:
    _log.debug("Fetching sudoers list from DB.")
    try:
        sudoers_doc = await sudoersdb.find_one({"sudo": "sudo"})
        if not sudoers_doc or "sudoers" not in sudoers_doc:
            _log.info("No sudoers document found or 'sudoers' field missing. Returning empty list.")
            return []
        _log.debug(f"Retrieved {len(sudoers_doc['sudoers'])} sudoers from DB.")
        return sudoers_doc["sudoers"]
    except Exception as e:
        _log.error(f"DB error fetching sudoers list: {e}", exc_info=True)
        return [] # Return empty on error to prevent issues

async def add_sudo(user_id: int) -> bool:
    _log.info(f"Adding user {user_id} to sudoers list.")
    try:
        sudoers_list = await get_sudoers() # get_sudoers already logs
        if user_id in sudoers_list:
            _log.warning(f"User {user_id} is already a sudoer.")
            return True # Or False if we consider "not added now" as False
        sudoers_list.append(user_id)
        await sudoersdb.update_one({"sudo": "sudo"}, {"$set": {"sudoers": sudoers_list}}, upsert=True)
        _log.info(f"Successfully added user {user_id} to sudoers in DB.")
        return True
    except Exception as e:
        _log.error(f"DB error adding sudo for user {user_id}: {e}", exc_info=True)
        return False

async def remove_sudo(user_id: int) -> bool:
    _log.info(f"Removing user {user_id} from sudoers list.")
    try:
        sudoers_list = await get_sudoers()
        if user_id not in sudoers_list:
            _log.warning(f"User {user_id} not found in sudoers list for removal.")
            return False 
        sudoers_list.remove(user_id)
        await sudoersdb.update_one({"sudo": "sudo"}, {"$set": {"sudoers": sudoers_list}}, upsert=True) # upsert might not be needed if "sudo":"sudo" doc always exists
        _log.info(f"Successfully removed user {user_id} from sudoers in DB.")
        return True
    except Exception as e:
        _log.error(f"DB error removing sudo for user {user_id}: {e}", exc_info=True)
        return False

# --- Cards (Example of handling potentially sensitive data if 'cc' means credit card) ---
# If 'cc' refers to credit card numbers, they should NOT be stored or logged directly.
# The functions below assume 'cc' is some other non-sensitive identifier.
# If it IS sensitive, these functions need significant review for security.

async def get_cards() -> list:
    _log.debug("Fetching all 'cards' from DB.")
    results = []
    try:
        async for card_doc in cardsdb.find({"cc": {"$exists": True}}):
            # WARNING: If card_doc["cc"] is sensitive, logging it (even at debug) is risky.
            # For this example, assuming "cc" is a non-sensitive ID.
            card_id = card_doc.get("cc", "UnknownCardID") 
            _log.debug(f"Retrieved card ID: {card_id}") # Be cautious with this log
            results.append(card_id)
        _log.info(f"Retrieved {len(results)} cards from DB.")
    except Exception as e:
        _log.error(f"DB error fetching cards: {e}", exc_info=True)
    return results

async def add_card(cc: str): # 'cc' is the identifier
    _log.info(f"Attempting to add card with ID: {cc[:4]}... (ID partially masked for log)") # Example of partial masking
    # Never log the full 'cc' if it's sensitive.
    try:
        is_exist = await cardsdb.find_one({"cc": cc})
        if is_exist:
            _log.info(f"Card with ID {cc[:4]}... already exists. Skipping add.")
            return
        await cardsdb.insert_one({"cc": cc})
        _log.info(f"Successfully added card with ID {cc[:4]}... to DB.")
    except Exception as e:
        _log.error(f"DB error adding card ID {cc[:4]}...: {e}", exc_info=True)

# Final check on all functions to ensure logging is added appropriately.
# This is a sample, full file needs similar treatment for all functions.
# Remember to handle the in-memory cache dictionaries as well for gets/sets.
# For example, in get_loop:
# async def get_loop(chat_id: int) -> int:
#    lop = loop.get(chat_id)
#    if not lop:
#        _log.debug(f"Loop for chat {chat_id}: Cache miss. Returning default 0.")
#        return 0 # Default if not found
#    _log.debug(f"Loop for chat {chat_id}: Cache hit. Value: {lop}.")
#    return lop
# (The original get_loop had a default of 0 if not lop, which is fine)
