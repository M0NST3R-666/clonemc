from Clonify.misc import SUDOERS
from Clonify.utils.database import get_lang, is_maintenance
from strings import get_string # This function provides the actual localized strings
from config import SUPPORT_CHAT
from Clonify import app, LOGGER # Added LOGGER

_log = LOGGER(__name__) # Added logger instance

def language(mystic):
    """Decorator to fetch and inject language strings for message handlers."""
    async def wrapper(_, message, **kwargs): # _ is often client, but here it's unused by decorator itself
        user = message.from_user
        chat = message.chat
        func_name = mystic.__name__
        _log.debug(f"Language decorator called for '{func_name}' by user {user.id} in chat {chat.id}.")

        if await is_maintenance() is False:
            if user.id not in SUDOERS:
                _log.warning(f"Maintenance mode ON. User {user.id} (not sudoer) blocked by Language decorator for '{func_name}' in chat {chat.id}.")
                # It's unusual for a language decorator to block access. This might be a global check.
                return await message.reply_text(
                    text=f"{app.mention} ɪs ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ, ᴠɪsɪᴛ <a href={SUPPORT_CHAT}>sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ</a> ғᴏʀ ᴋɴᴏᴡɪɴɢ ᴛʜᴇ ʀᴇᴀsᴏɴ.",
                    disable_web_page_preview=True,
                )
        
        # Message deletion is also unusual for a language decorator.
        # This might indicate the decorator is doing more than just language handling.
        # try:
        #     await message.delete() # Original code had this. Re-evaluating if it belongs here.
        #     _log.debug(f"Deleted original message {message.id} in chat {chat.id} (Language decorator).")
        # except Exception as e_del:
        #     _log.warning(f"Failed to delete message {message.id} in chat {chat.id} (Language decorator): {e_del}")
        # Decided to comment out message.delete() as it's not typical for a language decorator's core role.
        # If deletion is desired, it should ideally be in a more specific decorator or the handler itself.

        lang_code = "en" # Default language
        try:
            lang_code = await get_lang(chat.id) # Fetches preferred lang for the chat
            language_strings = get_string(lang_code) # Gets the dictionary of strings
            _log.debug(f"Language for chat {chat.id} is '{lang_code}' (Decorator: language).")
        except Exception as e_lang:
            _log.error(f"Error getting language for chat {chat.id} in Language decorator: {e_lang}. Defaulting to 'en'.")
            language_strings = get_string("en") # Fallback to English
        
        # The wrapped function will receive 'language_strings' (often named '_') as an argument.
        return await mystic(_, message, language_strings, **kwargs) # Pass client, message, lang_strings

    return wrapper


def languageCB(mystic):
    """Decorator to fetch and inject language strings for callback query handlers."""
    async def wrapper(_, CallbackQuery, **kwargs): # _ is client
        user = CallbackQuery.from_user
        chat = CallbackQuery.message.chat
        func_name = mystic.__name__
        cb_data = CallbackQuery.data[:30] if CallbackQuery.data else "NoData"
        _log.debug(f"LanguageCB decorator called for callback '{cb_data}' (handler: '{func_name}') by user {user.id} in chat {chat.id}.")

        if await is_maintenance() is False:
            if user.id not in SUDOERS:
                _log.warning(f"Maintenance mode ON. User {user.id} (not sudoer) blocked by LanguageCB for callback '{cb_data}' in chat {chat.id}.")
                try:
                    return await CallbackQuery.answer(
                        f"{app.mention} ɪs ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ, ᴠɪsɪᴛ sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ ғᴏʀ ᴋɴᴏᴡɪɴɢ ᴛʜᴇ ʀᴇᴀsᴏɴ.",
                        show_alert=True,
                    )
                except Exception as e_ans:
                     _log.warning(f"Error answering maintenance callback for user {user.id}: {e_ans}")
                return # Stop execution

        lang_code = "en" # Default
        try:
            lang_code = await get_lang(chat.id)
            language_strings = get_string(lang_code)
            _log.debug(f"Language for chat {chat.id} is '{lang_code}' (Decorator: languageCB).")
        except Exception as e_lang:
            _log.error(f"Error getting language for chat {chat.id} in LanguageCB decorator: {e_lang}. Defaulting to 'en'.")
            language_strings = get_string("en")
        
        return await mystic(_, CallbackQuery, language_strings, **kwargs)

    return wrapper


def LanguageStart(mystic):
    """Simplified language decorator, primarily for /start commands where maintenance/delete might not be desired."""
    async def wrapper(_, message, **kwargs): # _ is client
        user = message.from_user
        chat = message.chat
        func_name = mystic.__name__
        _log.debug(f"LanguageStart decorator called for '{func_name}' by user {user.id} in chat {chat.id}.")
        
        lang_code = "en" # Default
        try:
            lang_code = await get_lang(chat.id)
            language_strings = get_string(lang_code)
            _log.debug(f"Language for chat {chat.id} is '{lang_code}' (Decorator: LanguageStart).")
        except Exception as e_lang:
            _log.error(f"Error getting language for chat {chat.id} in LanguageStart decorator: {e_lang}. Defaulting to 'en'.")
            language_strings = get_string("en")
            
        # Note: Maintenance check and message deletion are NOT part of this simplified decorator.
        # This makes it cleaner for handlers like /start that might have their own specific logic for these.
        return await mystic(_, message, language_strings, **kwargs)

    return wrapper
