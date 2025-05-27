from pyrogram import Client, errors # Added errors for exception handling

import config

# Assuming LOGGER is initialized in the parent package or a shared logging module
from ..logging import LOGGER
_log = LOGGER(__name__)

assistants = [] # List to store string session names that are active
assistantids = [] # List to store user IDs of active assistants

class Userbot(Client):
    def __init__(self):
        _log.info("Initializing Userbot Clients (Assistants)...")
        # Initialize clients for each string session if provided in config
        # For this example, only STRING1 is shown as in the original.
        # A more scalable approach would loop through config.STRING_SESSIONS or similar.
        
        self.one = None # Default to None
        if config.STRING1:
            try:
                self.one = Client(
                    name="PROAss1", # Consider making name unique if multiple Userbots are instantiated
                    api_id=config.API_ID,
                    api_hash=config.API_HASH,
                    session_string=str(config.STRING1),
                    no_updates=True, # Usually True for assistants unless specific updates are needed
                )
                _log.debug("Userbot Client instance for STRING1 created.")
            except Exception as e:
                _log.error(f"Error initializing Userbot Client for STRING1: {e}", exc_info=True)
                # self.one remains None, start() will handle this.
        else:
            _log.info("STRING1 not provided, Assistant 1 will not be started.")


    async def start(self):
        _log.info("Starting Assistant Clients...")
        if self.one and config.STRING1: # Check if client was initialized and string exists
            _log.info("Starting Assistant 1 (self.one)...")
            try:
                await self.one.start()
                self.one.id = self.one.me.id
                self.one.name = self.one.me.first_name + (" " + self.one.me.last_name if self.one.me.last_name else "")
                self.one.username = self.one.me.username
                _log.info(f"Assistant 1 started as @{self.one.username} (ID: {self.one.id}, Name: {self.one.name}).")
                assistants.append(1) # Mark assistant 1 as active (using number 1)
                assistantids.append(self.one.id)

                # Join specified chats (optional, good for logging or support)
                # These should ideally be configurable and handled gracefully if join fails.
                try:
                    await self.one.join_chat("ProBotGc")
                    _log.debug(f"Assistant @{self.one.username} attempted to join ProBotGc.")
                except errors.UserAlreadyParticipant:
                    _log.debug(f"Assistant @{self.one.username} is already a participant in ProBotGc.")
                except Exception as e_join1:
                    _log.warning(f"Assistant @{self.one.username} failed to join ProBotGc: {type(e_join1).__name__} - {e_join1}")
                
                try:
                    await self.one.join_chat("ProBotts")
                    _log.debug(f"Assistant @{self.one.username} attempted to join ProBotts.")
                except errors.UserAlreadyParticipant:
                    _log.debug(f"Assistant @{self.one.username} is already a participant in ProBotts.")
                except Exception as e_join2:
                    _log.warning(f"Assistant @{self.one.username} failed to join ProBotts: {type(e_join2).__name__} - {e_join2}")

                if config.LOGGER_ID:
                    try:
                        await self.one.send_message(config.LOGGER_ID, f"Assistant @{self.one.username} (ID: {self.one.id}) started.")
                        _log.info(f"Assistant @{self.one.username} sent start confirmation to LOGGER_ID {config.LOGGER_ID}.")
                    except Exception as e_log_send:
                        _log.error(
                            f"Assistant @{self.one.username} failed to send start message to log group {config.LOGGER_ID}. "
                            f"Reason: {type(e_log_send).__name__} - {e_log_send}. "
                            "Ensure assistant is in the log group and can send messages."
                        )
                        # Not exiting here, as the main bot might still function.
                else:
                    _log.warning("LOGGER_ID not configured. Assistant start message not sent to log group.")

            except errors.AuthKeyError: # Common error for bad session strings
                 _log.error(f"Authentication failed for Assistant 1 (STRING1). Session string might be invalid or revoked.", exc_info=True)
                 # exit() was here, but it might be too drastic if other assistants or the main bot can run.
                 # Consider a mechanism to flag this assistant as non-operational.
            except Exception as e_start:
                _log.error(f"Failed to start Assistant 1 (STRING1): {type(e_start).__name__} - {e_start}", exc_info=True)
                # exit() was here.
        else:
            if config.STRING1 and not self.one: # String was provided but client init failed
                 _log.error("Assistant 1 (self.one) was not initialized properly, cannot start.")
            else: # No string1 provided
                 _log.info("Assistant 1 (self.one) not configured to start.")
        
        # Placeholder for starting other assistants (STRING2, STRING3, etc.)
        # if config.STRING2: await self.two.start() ... and so on.
        
        if not assistants: # No assistants were successfully started
            _log.warning("No assistant clients were started. Some functionalities might be limited.")


    async def stop(self):
        _log.info("Stopping Assistant Clients...")
        try:
            if self.one and self.one.is_connected and 1 in assistants: # Check if it was started and active
                await self.one.stop()
                _log.info("Assistant 1 (self.one) stopped.")
        except Exception as e_stop1:
            _log.error(f"Error stopping Assistant 1 (self.one): {e_stop1}", exc_info=True)
        
        # Placeholder for stopping other assistants
        # if self.two and config.STRING2: await self.two.stop() ...

        _log.info("All configured assistant clients have been processed for stopping.")
