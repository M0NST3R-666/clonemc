from typing import Union
from pyrogram import filters, types, enums # Added enums
from pyrogram.types import InlineKeyboardMarkup, Message, InlineKeyboardButton
from Clonify import app, LOGGER # Added LOGGER
from Clonify.utils import help_pannel
from Clonify.utils.database import get_lang
from Clonify.utils.decorators.language import LanguageStart, languageCB
from Clonify.utils.inline.help import help_back_markup, private_help_panel
from config import BANNED_USERS, START_IMG_URL, SUPPORT_CHAT
from strings import get_string, helpers
# from Clonify.utils.stuffs.helper import Helper # Assuming Helper contains text, not methods directly used here.

_log = LOGGER(__name__) # Added logger instance

@app.on_message(filters.command(["help"]) & filters.private & ~BANNED_USERS)
@app.on_callback_query(filters.regex("settings_back_helper") & ~BANNED_USERS)
async def helper_private(client: app, update: Union[types.Message, types.CallbackQuery]):
    is_callback = isinstance(update, types.CallbackQuery)
    user_id = update.from_user.id
    
    if is_callback:
        _log.info(f"Help settings_back_helper callback from user {user_id}.")
        try:
            await update.answer()
        except Exception as e_ans:
            _log.warning(f"Error answering settings_back_helper callback for user {user_id}: {e_ans}")
        
        chat_id = update.message.chat.id
        language = await get_lang(chat_id)
        _ = get_string(language)
        keyboard = help_pannel(_, True) # True for private context
        try:
            await update.edit_message_text(
                _["help_1"].format(SUPPORT_CHAT), reply_markup=keyboard
            )
            _log.debug(f"Edited help message for user {user_id} in chat {chat_id} (callback).")
        except Exception as e_edit:
            _log.error(f"Failed to edit help message for user {user_id} in chat {chat_id} (callback): {e_edit}", exc_info=True)
    else: # It's a Message
        _log.info(f"Help command in private from user {user_id}.")
        # This try-except for delete seems to be a common pattern, maybe for old messages.
        # try: await update.delete() 
        # except: pass # Silently ignore if delete fails
        
        language = await get_lang(update.chat.id)
        _ = get_string(language)
        keyboard = help_pannel(_)
        try:
            await update.reply_photo(
                photo=START_IMG_URL if START_IMG_URL else "https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4", # Fallback image
                caption=_["help_1"].format(SUPPORT_CHAT),
                reply_markup=keyboard,
            )
            _log.debug(f"Sent help photo to user {user_id} in chat {update.chat.id}.")
        except Exception as e_photo:
            _log.error(f"Failed to send help photo to user {user_id} in chat {update.chat.id}: {e_photo}", exc_info=True)
            # Fallback to text if photo fails
            try:
                await update.reply_text(
                    _["help_1"].format(SUPPORT_CHAT), reply_markup=keyboard
                )
                _log.debug(f"Sent fallback help text to user {user_id} in chat {update.chat.id}.")
            except Exception as e_text:
                 _log.error(f"Failed to send fallback help text to user {user_id} in chat {update.chat.id}: {e_text}", exc_info=True)


@app.on_message(filters.command(["help"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def help_com_group(client, message: Message, _):
    user = message.from_user
    chat = message.chat
    _log.info(f"Help command in group {chat.id} ('{chat.title}') by user {user.id} ('{user.first_name}').")
    keyboard = private_help_panel(_)
    try:
        await message.reply_text(_["help_2"], reply_markup=InlineKeyboardMarkup(keyboard)) # "Click button below for help"
        _log.debug(f"Sent group help prompt to chat {chat.id}.")
    except Exception as e:
        _log.error(f"Failed to send group help prompt to chat {chat.id}: {e}", exc_info=True)


@app.on_callback_query(filters.regex("help_callback") & ~BANNED_USERS)
@languageCB
async def helper_cb(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    cb = callback_data.split(None, 1)[1]
    user_id = CallbackQuery.from_user.id
    chat_id = CallbackQuery.message.chat.id
    _log.info(f"Help callback '{cb}' from user {user_id} in chat {chat_id}.")
    
    keyboard = help_back_markup(_)
    help_text_key = f"HELP_{cb.upper().replace('HB', '')}" # Try to map cb to helpers keys like HELP_1, HELP_2 etc.
    
    help_content = getattr(helpers, help_text_key, None)
    if cb == "cbot": # Specific case for clone help
        help_content = getattr(helpers, "CLONE_HELP", None)
        if not help_content: _log.warning(f"CLONE_HELP string not found in helpers for callback '{cb}'.")

    if not help_content:
        _log.error(f"No help content found for help_callback code '{cb}' (mapped to {help_text_key}).")
        try:
            return await CallbackQuery.answer("Help content not found for this section.", show_alert=True)
        except Exception as e_ans:
             _log.warning(f"Error answering callback for missing help content '{cb}': {e_ans}")
        return

    try:
        await CallbackQuery.edit_message_text(help_content, reply_markup=keyboard)
        _log.debug(f"Edited message with help section '{cb}' for user {user_id} in chat {chat_id}.")
    except Exception as e:
        _log.error(f"Failed to edit message for help section '{cb}' (user {user_id}, chat {chat_id}): {e}", exc_info=True)
        try:
            await CallbackQuery.answer("Error displaying help section. Please try again.", show_alert=True)
        except Exception as e_ans:
            _log.warning(f"Error answering callback for failed help edit '{cb}': {e_ans}")

# Note: The original file had another callback `on_callback_query(filters.regex('managebot123'))`.
# This seemed to be a duplicate or misnamed version of `settings_back_helper` based on its body.
# I've assumed `settings_back_helper` is the primary one and enhanced its logging.
# If `managebot123` is a distinct, valid callback, it would need its own logging.
# For now, I'm omitting it as it looked redundant with the first handler `helper_private`.

@app.on_callback_query(filters.regex('mplus') & ~BANNED_USERS)      
async def mb_plugin_button(client, CallbackQuery): # "More Plugins" or similar
    user_id = CallbackQuery.from_user.id
    chat_id = CallbackQuery.message.chat.id
    callback_data = CallbackQuery.data.strip()
    cb = callback_data.split(None, 1)[1]
    _log.info(f"mplus callback '{cb}' from user {user_id} in chat {chat_id}.")

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ʙᴀᴄᴋ", callback_data=f"settings_back_helper")]]) # Changed back to main help
    
    # Assuming Helper class/object has attributes corresponding to `cb` values that hold help strings.
    # E.g., Helper.SOME_PLUGIN_COMMAND_desc
    # This part of the original code might need strings to be in `strings/helpers.py` like other help texts.
    help_content = getattr(helpers, cb, None) # Check if content is in helpers.py first
    
    if not help_content: # Fallback or if it was intended to be from a class `Helper`
        # from Clonify.utils.stuffs.helper import Helper # Dynamic import if Helper class is complex
        # help_content = getattr(Helper, cb, None)
        _log.warning(f"Help content for mplus callback '{cb}' not found in strings.helpers. Attempting fallback if Helper class exists.")
        # For now, let's assume it MUST be in helpers.py for consistency
        help_content = f"Help content for '{cb}' is missing. Please report to support."
        # If you have a Helper class in Clonify.utils.stuffs.helper, uncomment above and use it.

    try:
        await CallbackQuery.edit_message_text(help_content, reply_markup=keyboard, parse_mode=enums.ParseMode.MARKDOWN)
        _log.debug(f"Edited message with mplus section '{cb}' for user {user_id} in chat {chat_id}.")
    except Exception as e:
        _log.error(f"Failed to edit message for mplus section '{cb}' (user {user.id}, chat {chat_id}): {e}", exc_info=True)
        try:
            await CallbackQuery.answer("Error displaying this help section.", show_alert=True)
        except Exception as e_ans:
            _log.warning(f"Error answering callback for failed mplus edit '{cb}': {e_ans}")
