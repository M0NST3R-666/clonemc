import asyncio
import importlib

from pyrogram import idle
from pyrogram import errors as pyrogram_errors # Added import
from pytgcalls.exceptions import NoActiveGroupCall

import config
from Clonify import LOGGER, app, userbot
from Clonify.core.call import PRO
from Clonify.misc import sudo
from Clonify.plugins import ALL_MODULES
from Clonify.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS
from Clonify.plugins.tools.clone import restart_bots


async def init():
    # Essential configuration checks
    if not config.API_ID:
        LOGGER(__name__).critical("API_ID not found in config. Exiting.")
        exit()
    if not config.API_HASH:
        LOGGER(__name__).critical("API_HASH not found in config. Exiting.")
        exit()
    if not config.BOT_TOKEN:
        LOGGER(__name__).critical("BOT_TOKEN not found in config. Exiting.")
        exit()
    if not config.STRING1: # Kept existing check for STRING1
        LOGGER(__name__).error("String Session not filled, please provide a valid session.")
        exit()

    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except Exception as e: # Catch specific exception
        LOGGER(__name__).warning(f"Failed to load banned users: {e}")
        pass # Or handle more gracefully

    # Start app (bot) client
    try:
        await app.start()
    except (ConnectionError, pyrogram_errors.AuthKeyError, pyrogram_errors.ApiIdInvalid, pyrogram_errors.PhoneNumberInvalid) as e:
        LOGGER(__name__).critical(f"Error starting bot client: {e}. Please check your API_ID, API_HASH, and BOT_TOKEN.")
        exit()
    except Exception as e:
        LOGGER(__name__).critical(f"An unexpected error occurred while starting bot client: {e}")
        exit()

    for all_module in ALL_MODULES:
        importlib.import_module("Clonify.plugins" + all_module)
    LOGGER("Clonify.plugins").info("𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳...")

    # Start userbot client
    try:
        await userbot.start()
    except (ConnectionError, pyrogram_errors.AuthKeyError, pyrogram_errors.UserDeactivatedBan, pyrogram_errors.AuthKeyUnregistered) as e:
        LOGGER(__name__).critical(f"Error starting userbot client: {e}. Please check your STRING_SESSION.")
        exit()
    except Exception as e:
        LOGGER(__name__).critical(f"An unexpected error occurred while starting userbot client: {e}")
        exit()
    
    # Start PyTgCalls client
    try:
        await PRO.start()
    except (ConnectionError, pyrogram_errors.AuthKeyError) as e: # PRO.start() might also have similar auth issues
        LOGGER(__name__).critical(f"Error starting PyTgCalls client: {e}. This could be related to userbot authentication.")
        exit()
    except Exception as e:
        LOGGER(__name__).critical(f"An unexpected error occurred while starting PyTgCalls client: {e}")
        exit()

    try:
        await PRO.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("Clonify").error(
            "No active group call found. "
            "Please ensure the bot is in a group/channel with an active voice chat "
            "and that the LOGGER_ID in your config is correctly set to this group/channel's ID. "
            "Music Bot stopping."
        )
        exit()
    except Exception as e: # Catch specific exception and log it
        LOGGER("Clonify").error(f"An error occurred during stream_call: {type(e).__name__} - {e}")
        pass # Decide if exiting is necessary or if it can recover/continue

    await PRO.decorators()
    await restart_bots()
    LOGGER("Clonify").info(
        "╔═════ஜ۩۞۩ஜ════╗\n  ☠︎︎𝗠𝗔𝗗𝗘 𝗕𝗬 𝗣𝗿𝗼𝗕𝗼t𝘀☠︎︎\n╚═════ஜ۩۞۩ஜ════╝"
    )
    await idle()
    await app.stop()
    await userbot.stop()
    LOGGER("Clonify").info("𝗦𝗧𝗢𝗣 𝗠𝗨𝗦𝗜𝗖🎻 𝗕𝗢𝗧..")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
